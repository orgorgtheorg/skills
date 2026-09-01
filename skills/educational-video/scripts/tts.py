"""Narrate every section with Piper (offline, CPU, ~150 MB RAM).
Usage: python3 scripts/tts.py [--speed 1.15] [--voice en_US-lessac-medium]
Writes audio/<id>.wav (already speed-adjusted) and audio/timings.txt.
"""
import argparse, os, sys, wave
sys.path.insert(0, os.path.dirname(__file__))
from common import AUDIO_DIR, ffmpeg_exe, duration, load_sections, run

ap = argparse.ArgumentParser()
ap.add_argument("--speed", type=float, default=1.15)
ap.add_argument("--voice", default=os.environ.get("VOICE", "en_US-lessac-medium"))
ap.add_argument("--voice-dir", default=os.path.expanduser("~/.local/share/piper-voices"))
ap.add_argument("--only", nargs="*", help="section ids to (re)generate")
args = ap.parse_args()

try:
    from piper import PiperVoice  # >= 1.3
    NEW_API = True
except ImportError:
    from piper.voice import PiperVoice  # 1.2
    NEW_API = False

onnx = os.path.join(args.voice_dir, f"{args.voice}.onnx")
voice = PiperVoice.load(onnx, os.path.join(args.voice_dir, f"{args.voice}.onnx.json"))
os.makedirs(AUDIO_DIR, exist_ok=True)

sections = load_sections()
for sid, text in sections:
    if args.only and sid not in args.only:
        continue
    raw = os.path.join(AUDIO_DIR, f"{sid}.raw.wav")
    final = os.path.join(AUDIO_DIR, f"{sid}.wav")
    with wave.open(raw, "wb") as wf:
        if NEW_API:
            voice.synthesize_wav(text, wf)
        else:
            voice.synthesize(text, wf)
    if abs(args.speed - 1.0) > 0.01:
        run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", raw,
             "-filter:a", f"atempo={args.speed}", "-acodec", "pcm_s16le", final])
        os.remove(raw)
    else:
        os.replace(raw, final)
    print(f"{sid:24s} {duration(final):6.1f}s")

with open(os.path.join(AUDIO_DIR, "timings.txt"), "w") as f:
    off = 0.0
    for sid, _ in sections:
        d = duration(os.path.join(AUDIO_DIR, f"{sid}.wav"))
        f.write(f"{sid}\t{off:.2f}\t{d:.2f}\n")
        off += d
print(f"total narration: {off/60:.1f} min")
