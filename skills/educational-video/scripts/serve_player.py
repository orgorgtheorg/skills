"""Serve output/ with a small HTML player so the video can be a `url` artifact.
Usage: nohup python3 scripts/serve_player.py --port 5180 --title "..." > player.log 2>&1 &
"""
import argparse, html, os, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.dirname(__file__))
from common import OUT_DIR

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=5180)
ap.add_argument("--title", default="Video")
args = ap.parse_args()

with open(os.path.join(OUT_DIR, "index.html"), "w") as f:
    f.write(f"""<!doctype html><meta charset=utf-8><title>{html.escape(args.title)}</title>
<style>html,body{{margin:0;height:100%;background:#0f0f1a;color:#eee;font:15px system-ui}}
main{{display:flex;flex-direction:column;align-items:center;gap:12px;padding:16px}}
video{{width:100%;max-width:1280px;border-radius:8px;background:#000}}a{{color:#8ab4ff}}</style>
<main><video controls preload=metadata poster=thumb.png src=final.mp4></video>
<h1 style="font-size:18px;margin:0">{html.escape(args.title)}</h1>
<a href=final.mp4 download>Download MP4</a></main>""")


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=OUT_DIR, **k)

    def log_message(self, *a):
        pass


ThreadingHTTPServer(("0.0.0.0", args.port), H).serve_forever()
