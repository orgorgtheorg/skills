#!/usr/bin/env python3
"""Turn a raw screen recording into an annotated demo video.

Captions sit in a band under the frame, a marker ring shows every tap, and the
waits between steps are cut. Times in the spec are times in the SOURCE video.

    python3 annotate.py spec.json

Spec:
{
  "source": "raw.mp4",
  "output": "demo.mp4",
  "captions": [[0.0, 6.5, "The app, signed out"], ...],
  "taps":     [[10.0, 11.0, 600, 2233], ...],   # start, end, x, y in source px
  "keep":     [[1.5, 7.5], [9.3, 12.5], ...],   # windows to keep, in order
  "height":   1280,            # optional output height (default 1280)
  "band":     190,             # optional caption band height in source px
  "font_size": 58              # optional caption size in source px
}

Leave "keep" out to keep everything. Leave "taps" out for a web recording that
already shows a cursor.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _tool(name: str) -> str:
    return shutil.which(name) or f"/opt/homebrew/bin/{name}"


def _font_path() -> str:
    for candidate in ("/System/Library/Fonts/Helvetica.ttc",
                      "/System/Library/Fonts/Supplemental/Arial.ttf",
                      "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(candidate).exists():
            return candidate
    raise SystemExit("no usable font found; set FONT in this script")


FONT = _font_path()
FFMPEG = _tool("ffmpeg")
FFPROBE = _tool("ffprobe")
MARKER_FRACTION = 0.215  # marker diameter as a share of the frame width


def probe_size(path: Path) -> tuple[int, int]:
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path)],
        capture_output=True, text=True, check=True).stdout.strip()
    w, h = out.split("x")[:2]
    return int(w), int(h)


def caption_png(text: str, path: Path, width: int, band: int, size: int) -> None:
    img = Image.new("RGBA", (width, band), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, size)
    box = d.textbbox((0, 0), text, font=font)
    x = (width - (box[2] - box[0])) // 2 - box[0]
    y = (band - (box[3] - box[1])) // 2 - box[1]
    d.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    img.save(path)


def marker_png(path: Path, diameter: int) -> None:
    img = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    edge = max(4, diameter // 26)
    d.ellipse([edge, edge, diameter - edge, diameter - edge],
              fill=(255, 59, 92, 70), outline=(255, 59, 92, 235), width=edge + 2)
    r = diameter // 10
    c = diameter // 2
    d.ellipse([c - r, c - r, c + r, c + r], fill=(255, 59, 92, 190))
    img.save(path)


def main(spec_path: str) -> None:
    spec = json.loads(Path(spec_path).read_text())
    base = Path(spec_path).parent
    src = (base / spec["source"]).resolve()
    out = (base / spec.get("output", "demo.mp4")).resolve()
    assets = out.parent / ".annotate-assets"
    assets.mkdir(exist_ok=True)

    w, h = probe_size(src)
    band = int(spec.get("band", round(h * 0.072)))
    font_size = int(spec.get("font_size", round(band * 0.31)))
    marker_d = int(round(w * MARKER_FRACTION))
    captions = spec.get("captions", [])
    taps = spec.get("taps", [])
    keep = spec.get("keep", [])

    for i, (_, _, text) in enumerate(captions):
        caption_png(text, assets / f"cap{i}.png", w, band, font_size)
    if taps:
        marker_png(assets / "marker.png", marker_d)

    inputs = ["-i", str(src)]
    for i in range(len(captions)):
        inputs += ["-i", str(assets / f"cap{i}.png")]
    if taps:
        inputs += ["-i", str(assets / "marker.png")]

    chain = [f"[0:v]fps=15,setpts=PTS-STARTPTS,pad=iw:ih+{band}:0:0:0x0B0D12[base]"]
    last = "[base]"
    for i, (a, b, _) in enumerate(captions):
        chain.append(f"{last}[{i + 1}:v]overlay=x=0:y={h}:enable='between(t,{a},{b})'[c{i}]")
        last = f"[c{i}]"
    for j, (a, b, cx, cy) in enumerate(taps):
        x, y = int(cx) - marker_d // 2, int(cy) - marker_d // 2
        chain.append(
            f"{last}[{len(captions) + 1}:v]overlay=x={x}:y={y}:"
            f"enable='between(t,{a},{b})'[m{j}]")
        last = f"[m{j}]"

    height = int(spec.get("height", 1280))
    if keep:
        chain.append(f"{last}split={len(keep)}" + "".join(f"[s{i}]" for i in range(len(keep))))
        for i, (a, b) in enumerate(keep):
            chain.append(f"[s{i}]trim=start={a}:end={b},setpts=PTS-STARTPTS[t{i}]")
        chain.append("".join(f"[t{i}]" for i in range(len(keep)))
                     + f"concat=n={len(keep)}:v=1:a=0,scale=-2:{height}[v]")
    else:
        chain.append(f"{last}scale=-2:{height}[v]")

    subprocess.run(
        [FFMPEG, "-y", *inputs, "-filter_complex", ";".join(chain), "-map", "[v]",
         "-c:v", "libx264", "-crf", "24", "-preset", "slow", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", "-an", str(out), "-loglevel", "error"],
        check=True)
    seconds = sum(b - a for a, b in keep) if keep else None
    print(f"wrote {out} ({out.stat().st_size // 1024} KB"
          + (f", about {seconds:.0f}s)" if seconds else ")"))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
