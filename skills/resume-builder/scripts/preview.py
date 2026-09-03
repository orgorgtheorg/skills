#!/usr/bin/env python3
"""preview.py — a live preview tab for the resumes under one folder.

usage:
  nohup python3 /.skills/resume-builder/scripts/preview.py [ROOT] [--port 5190] \
      > /workspace/resume/preview.log 2>&1 &
  orgorg-artifact add --id resume-<slug> --kind url --port 5190 --route /<slug>/ \
      --title "Resume — <target>" --live

ROOT defaults to /workspace/resume/targets. Every subfolder <slug> that holds a
render.py output is served at /<slug>/: the printed pages stacked like paper,
download links for the PDF and the .docx, and the last render's lint report.
The page polls /<slug>/status.json every two seconds and swaps the page images
the moment render.py writes new ones, so the tab keeps itself current. Never
`orgorg-artifact touch` it. / lists every target.

Idempotent: if the port is already taken, it says so and exits 0, so it is
safe to run again before every render.
"""

import argparse
import glob
import html
import json
import mimetypes
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = "/workspace/resume/targets"
PAGE_RE = re.compile(r"-(\d+)\.png$")

VIEWER = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { color-scheme: light; }
  html, body { margin: 0; background: #e5e7eb; color: #111827;
    font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  header { position: sticky; top: 0; z-index: 2; background: #fff; border-bottom: 1px solid #d1d5db;
    padding: 10px 16px; display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 16px; }
  header h1 { font-size: 15px; margin: 0; }
  header .status { color: #4b5563; }
  header nav { margin-left: auto; display: flex; gap: 12px; }
  header nav a { color: #1d4ed8; text-decoration: none; font-weight: 600; }
  main { max-width: 900px; margin: 0 auto; padding: 20px 12px 40px; }
  figure { margin: 0 0 22px; }
  figure img { display: block; width: 100%; background: #fff; box-shadow: 0 1px 2px rgba(0,0,0,.18), 0 8px 24px rgba(0,0,0,.12); }
  figcaption { text-align: center; color: #6b7280; font-size: 12px; margin-top: 8px; }
  .empty { text-align: center; color: #6b7280; padding: 80px 0; }
  section.report { background: #fff; border: 1px solid #d1d5db; border-radius: 6px; padding: 12px 16px; }
  section.report h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .04em; color: #6b7280; margin: 0 0 8px; }
  section.report ul { margin: 0 0 10px; padding-left: 18px; }
  section.report li.warn { color: #92400e; }
  section.report li.note { color: #4b5563; }
</style></head>
<body>
<header>
  <h1 id="title">__TITLE__</h1>
  <span class="status" id="status">Waiting for the first render…</span>
  <nav id="links"></nav>
</header>
<main>
  <div id="pages"><div class="empty">Waiting for the first render…</div></div>
  <section class="report" id="report" hidden></section>
</main>
<script>
(function () {
  let last = null;
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  function render(s) {
    const r = s.report || {};
    const pages = s.pages || [];
    const parts = [];
    if (pages.length) parts.push(`${pages.length} page${pages.length === 1 ? "" : "s"}`);
    if (r.theme) parts.push(r.theme);
    if (r.paper) parts.push(r.paper);
    if (r.scale && r.scale !== 1) parts.push(`type at ${Math.round(r.scale * 100)}%`);
    if (r.rendered_at) parts.push(`rendered ${new Date(r.rendered_at).toLocaleTimeString()}`);
    document.getElementById("status").textContent = parts.length ? parts.join(" · ") : "Waiting for the first render…";
    if (r.name) { document.getElementById("title").textContent = r.name; document.title = r.name + " — preview"; }
    const links = [];
    if (s.pdf) links.push(`<a href="${esc(s.pdf)}?v=${s.updated}" download>Download PDF</a>`);
    if (s.docx) links.push(`<a href="${esc(s.docx)}?v=${s.updated}" download>Word</a>`);
    document.getElementById("links").innerHTML = links.join("");
    const el = document.getElementById("pages");
    if (!pages.length) {
      el.innerHTML = '<div class="empty">Waiting for the first render…</div>';
    } else {
      el.innerHTML = pages.map((p, i) =>
        `<figure><img src="${esc(p.name)}?v=${p.mtime}" alt="Page ${i + 1}"><figcaption>Page ${i + 1} of ${pages.length}</figcaption></figure>`
      ).join("");
    }
    const rep = document.getElementById("report");
    const items = [];
    (r.warnings || []).forEach((w) => items.push(`<li class="warn">${esc(w)}</li>`));
    (r.notes || []).forEach((n) => items.push(`<li class="note">${esc(n)}</li>`));
    (r.text_check || []).forEach((n) => items.push(`<li class="note">Text check: ${esc(n)}</li>`));
    if (items.length) { rep.innerHTML = `<h2>Last render</h2><ul>${items.join("")}</ul>`; rep.hidden = false; }
    else { rep.hidden = true; }
  }
  async function tick() {
    try {
      const res = await fetch(`status.json?t=${Date.now()}`, { cache: "no-store" });
      const s = await res.json();
      if (s.updated !== last) { last = s.updated; render(s); }
    } catch (e) { /* the server is restarting; try again */ }
    setTimeout(tick, 2000);
  }
  tick();
})();
</script>
</body></html>
"""

INDEX = """<!doctype html><html><head><meta charset="utf-8"><title>Resume previews</title>
<style>body{font:15px system-ui,sans-serif;margin:32px;color:#111827}a{color:#1d4ed8}li{margin:6px 0}</style>
</head><body><h1 style="font-size:18px">Resume previews</h1>__BODY__</body></html>
"""


def safe_slug(value):
    return re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", value) is not None


def target_status(folder, slug):
    reports = sorted(glob.glob(os.path.join(folder, "*.render.json")), key=os.path.getmtime, reverse=True)
    report = None
    stem = None
    if reports:
        try:
            with open(reports[0], encoding="utf-8") as fh:
                report = json.load(fh)
            stem = os.path.basename(reports[0])[: -len(".render.json")]
        except (OSError, ValueError):
            report = None
    if stem is None:
        pdfs = sorted(glob.glob(os.path.join(folder, "*.pdf")), key=os.path.getmtime, reverse=True)
        if pdfs:
            stem = os.path.splitext(os.path.basename(pdfs[0]))[0]
    pages = []
    pdf = docx = None
    newest = 0  # milliseconds: render.py writes the PDF, the PNGs and the report within one second
    if stem:
        for path in glob.glob(os.path.join(folder, f"{stem}-*.png")):
            m = PAGE_RE.search(path)
            if m:
                mtime = int(os.path.getmtime(path) * 1000)
                pages.append((int(m.group(1)), {"name": os.path.basename(path), "mtime": mtime}))
                newest = max(newest, mtime)
        pages = [p for _, p in sorted(pages)]
        for ext in ("pdf", "docx"):
            candidate = os.path.join(folder, f"{stem}.{ext}")
            if os.path.exists(candidate):
                newest = max(newest, int(os.path.getmtime(candidate) * 1000))
                if ext == "pdf":
                    pdf = os.path.basename(candidate)
                else:
                    docx = os.path.basename(candidate)
    if reports:
        newest = max(newest, int(os.path.getmtime(reports[0]) * 1000))
    # The fingerprint the page polls: any file change, the report's own timestamp, or a page-count change.
    updated = f"{newest}:{(report or {}).get('rendered_at', '')}:{len(pages)}"
    return {"slug": slug, "stem": stem, "pdf": pdf, "docx": docx, "pages": pages,
            "report": report, "updated": updated}


class Handler(BaseHTTPRequestHandler):
    root = ROOT

    def log_message(self, *args):
        pass

    def send_bytes(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        parts = [p for p in path.split("/") if p]
        if not parts:
            return self.send_index()
        slug = parts[0]
        if not safe_slug(slug):
            return self.send_bytes(404, b"not found", "text/plain")
        folder = os.path.join(self.root, slug)
        if not os.path.isdir(folder):
            return self.send_bytes(404, b"no such target", "text/plain")
        if len(parts) == 1:
            if not path.endswith("/"):
                self.send_response(302)
                self.send_header("Location", f"/{slug}/")
                self.end_headers()
                return None
            page = VIEWER.replace("__TITLE__", html.escape(slug))
            return self.send_bytes(200, page.encode("utf-8"), "text/html; charset=utf-8")
        if len(parts) == 2 and parts[1] == "status.json":
            body = json.dumps(target_status(folder, slug)).encode("utf-8")
            return self.send_bytes(200, body, "application/json")
        if len(parts) == 2 and safe_slug(parts[1]) and ".." not in parts[1]:
            file_path = os.path.join(folder, parts[1])
            if os.path.isfile(file_path):
                with open(file_path, "rb") as fh:
                    data = fh.read()
                ctype = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
                return self.send_bytes(200, data, ctype)
        return self.send_bytes(404, b"not found", "text/plain")

    def send_index(self):
        items = []
        if os.path.isdir(self.root):
            for name in sorted(os.listdir(self.root)):
                if safe_slug(name) and os.path.isdir(os.path.join(self.root, name)):
                    status = target_status(os.path.join(self.root, name), name)
                    label = (status["report"] or {}).get("name") or name
                    pages = len(status["pages"])
                    suffix = f" — {pages} page{'s' if pages != 1 else ''}" if pages else " — not rendered yet"
                    items.append(f'<li><a href="/{html.escape(name)}/">{html.escape(label)}</a> ({html.escape(name)}){suffix}</li>')
        body = f"<ul>{''.join(items)}</ul>" if items else "<p>No targets yet. Render one with render.py.</p>"
        self.send_bytes(200, INDEX.replace("__BODY__", body).encode("utf-8"), "text/html; charset=utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default=ROOT, help="folder whose subfolders are targets")
    ap.add_argument("--port", type=int, default=5190)
    args = ap.parse_args()
    Handler.root = os.path.abspath(args.root)
    os.makedirs(Handler.root, exist_ok=True)
    try:
        server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    except OSError:
        print(f"preview: port {args.port} is already in use; assuming the preview server is running")
        return
    print(f"preview: serving {Handler.root} on :{args.port} (started {time.strftime('%H:%M:%S')})", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
