"""Render scenes ONE AT A TIME on this machine (4 vCPU / 4 GB: never in parallel).
Usage: python3 scripts/render.py [--quality m|h] [--only S01Hook ...]
  m = 720p30 draft (fast, use while iterating)   h = 1080p30 final
Then verifies every video is at least as long as its narration.
"""
import argparse, glob, os, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from common import AUDIO_DIR, PROJECT, RENDER_DIR, duration, load_sections, scene_name

ap = argparse.ArgumentParser()
ap.add_argument("--quality", choices=["m", "h"], default="m")
ap.add_argument("--only", nargs="*")
args = ap.parse_args()

os.makedirs(RENDER_DIR, exist_ok=True)
media = os.path.join(PROJECT, "media")
failed = []
for sid, _ in load_sections():
    name = scene_name(sid)
    if args.only and name not in args.only:
        continue
    t0 = time.time()
    r = subprocess.run(
        ["manim", "render", f"-q{args.quality}", "--fps", "30", "--disable_caching",
         "--media_dir", media, "scenes.py", name],
        capture_output=True, text=True, cwd=PROJECT)
    if r.returncode != 0:
        print(f"FAILED {name}\n{r.stderr[-1500:]}")
        failed.append(name)
        continue
    mp4s = glob.glob(os.path.join(media, "videos", "scenes", "*", f"{name}.mp4"))
    if not mp4s:
        print(f"NO MP4 {name}")
        failed.append(name)
        continue
    dst = os.path.join(RENDER_DIR, f"{name}.mp4")
    shutil.move(max(mp4s, key=os.path.getmtime), dst)
    print(f"{name:24s} {duration(dst):6.1f}s  ({time.time()-t0:.0f}s render)")
shutil.rmtree(os.path.join(media, "videos"), ignore_errors=True)  # keep the disk small

print("\n== duration check (video must be >= audio)")
frozen = 0.0
for sid, _ in load_sections():
    name = scene_name(sid)
    v, a = os.path.join(RENDER_DIR, f"{name}.mp4"), os.path.join(AUDIO_DIR, f"{sid}.wav")
    if not (os.path.exists(v) and os.path.exists(a)):
        continue
    vd, ad = duration(v), duration(a)
    gap = ad - vd
    frozen += max(0.0, gap)
    print(f"{name:24s} vid={vd:6.1f}s aud={ad:6.1f}s gap={gap:+5.1f}s {'OK' if vd >= ad - 1 else 'SHORT'}")
print(f"frozen-frame total: {frozen:.1f}s (target 0)")
if failed:
    print(f"\n{len(failed)} scene(s) failed: {', '.join(failed)}")
    sys.exit(1)
