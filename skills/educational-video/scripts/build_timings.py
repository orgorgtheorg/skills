"""Per-sentence timing map: audio/<id>.wav + narration -> timings.json.
Word-count proportional split of the real audio duration. Prints the D arrays
to paste into scenes.py.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import AUDIO_DIR, PROJECT, duration, load_sections, scene_name


def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


out = {}
for sid, text in load_sections():
    wav = os.path.join(AUDIO_DIR, f"{sid}.wav")
    if not os.path.exists(wav):
        continue
    total = duration(wav)
    sents = split_sentences(text)
    words = sum(len(s.split()) for s in sents)
    rows, off = [], 0.0
    for s in sents:
        d = len(s.split()) / words * total
        rows.append({"start": round(off, 2), "end": round(off + d, 2), "duration": round(d, 2), "text": s})
        off += d
    out[sid] = {"duration": round(total, 2), "sentences": rows}
    print(f"\n# {scene_name(sid)}: {total:.1f}s, {len(rows)} sentences")
    print(f"D = {[r['duration'] for r in rows]}")
    for i, r in enumerate(rows):
        print(f"#   [{i}] {r['duration']:5.2f}s  {r['text'][:70]}")

with open(os.path.join(PROJECT, "timings.json"), "w") as f:
    json.dump(out, f, indent=2)
print("\nwrote timings.json")
