"""Captions + narration + concat -> output/final.mp4.
Usage: python3 scripts/compose.py [--no-captions]
Per section: extend video to the audio (clone last frame), burn ASS captions when
the ffmpeg build has libass (else write .srt next to the section), mux narration.
Then concat with a fast preset. Runs sequentially and single-process.
"""
import argparse, os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import AUDIO_DIR, OUT_DIR, PROJECT, RENDER_DIR, duration, ffmpeg_exe, load_sections, run, scene_name

ap = argparse.ArgumentParser()
ap.add_argument("--no-captions", action="store_true")
args = ap.parse_args()
FF = ffmpeg_exe()
os.makedirs(OUT_DIR, exist_ok=True)
CAP_DIR = os.path.join(PROJECT, "captions")
os.makedirs(CAP_DIR, exist_ok=True)

filters = subprocess.run([FF, "-hide_banner", "-filters"], capture_output=True, text=True).stdout
HAS_ASS = (" ass " in filters) and not args.no_captions


def ass_time(s):
    return f"{int(s//3600)}:{int(s%3600//60):02d}:{s%60:05.2f}"


def srt_time(s):
    ms = int(round((s - int(s)) * 1000))
    return f"{int(s//3600):02d}:{int(s%3600//60):02d}:{int(s%60):02d},{ms:03d}"


def write_captions(sid, text, dur):
    words = text.split()
    tpw = dur / len(words)
    chunk = 5
    ass = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nScaledBorderAndShadow: yes\n\n"
           "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
           "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
           "MarginL, MarginR, MarginV, Encoding\n"
           "Style: Default,Liberation Sans,54,&H00FFFFFF,&H0000FFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,4,3,3,2,40,40,30,1\n\n"
           "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    srt, n = "", 0
    for i0 in range(0, len(words), chunk):
        group = words[i0:i0 + chunk]
        for i, _ in enumerate(group):
            st, en = (i0 + i) * tpw, (i0 + i + 1) * tpw
            line = " ".join((r"{\c&H00D4FF&\b1}" + w + r"{\c&HFFFFFF&\b0}") if j == i else w for j, w in enumerate(group))
            ass += f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Default,,0,0,0,,{line}\n"
        n += 1
        srt += f"{n}\n{srt_time(i0*tpw)} --> {srt_time(min(len(words),i0+chunk)*tpw)}\n{' '.join(group)}\n\n"
    ap_ = os.path.join(CAP_DIR, f"{sid}.ass")
    with open(ap_, "w") as f:
        f.write(ass)
    with open(os.path.join(CAP_DIR, f"{sid}.srt"), "w") as f:
        f.write(srt)
    return ap_


parts = []
for idx, (sid, text) in enumerate(load_sections()):
    name = scene_name(sid)
    vid, aud = os.path.join(RENDER_DIR, f"{name}.mp4"), os.path.join(AUDIO_DIR, f"{sid}.wav")
    vd, ad = duration(vid), duration(aud)
    cap = write_captions(sid, text, ad)
    vf = []
    if vd < ad:
        vf.append(f"tpad=stop_mode=clone:stop_duration={ad - vd + 0.5:.2f}")
    if HAS_ASS:
        vf.append("ass='" + cap.replace(":", r"\:").replace("'", r"\'") + "'")
    out = os.path.join(OUT_DIR, f"section_{idx:02d}.mp4")
    cmd = [FF, "-y", "-loglevel", "error", "-i", vid, "-i", aud]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += ["-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-threads", "4", "-c:a", "aac", "-b:a", "160k", "-t", f"{ad:.3f}", out]
    run(cmd)
    parts.append(out)
    print(f"{name:24s} {ad:6.1f}s  {'captions burned' if HAS_ASS else 'srt sidecar'}")

concat = os.path.join(OUT_DIR, "concat.txt")
with open(concat, "w") as f:
    for p in parts:
        f.write(f"file '{p}'\n")
final = os.path.join(OUT_DIR, "final.mp4")
run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", concat,
     "-c", "copy", "-movflags", "+faststart", final])
run([FF, "-y", "-loglevel", "error", "-ss", "3", "-i", final, "-frames:v", "1", os.path.join(OUT_DIR, "thumb.png")])
print(f"\nfinal: {final}  ({duration(final)/60:.1f} min, {os.path.getsize(final)/1e6:.0f} MB)")
