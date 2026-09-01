"""Mid-frame and end-frame PNGs of every rendered scene -> verify/. Look at them
(read tool) for overlapping text, clipped content, and anything below the caption
floor. Fix scenes.py, re-render only the bad scenes, repeat.
"""
import glob, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import PROJECT, RENDER_DIR, duration, ffmpeg_exe, run

out = os.path.join(PROJECT, "verify")
os.makedirs(out, exist_ok=True)
for v in sorted(glob.glob(os.path.join(RENDER_DIR, "*.mp4"))):
    name = os.path.basename(v)[:-4]
    d = duration(v)
    for tag, t in (("mid", d / 2), ("end", max(0.0, d - 0.5))):
        run([ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", v, "-frames:v", "1",
             os.path.join(out, f"{name}_{tag}.png")])
    print(name)
print(f"frames in {out}/")
