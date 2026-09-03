#!/usr/bin/env python3
"""preview.py — a live preview tab for the resumes under one folder.

usage:
  nohup python3 /.skills/resume-builder/scripts/preview.py [ROOT] [--port 5190] \
      > /workspace/resume/preview.log 2>&1 &
  orgorg-artifact add --id resume-<slug> --kind url --port 5190 --route /<slug>/ \
      --title "Resume — <target>" --live

ROOT defaults to /workspace/resume/targets. Every subfolder <slug> that holds a
render.py output is served at /<slug>/: the printed pages stacked like paper,
download links for the PDF and the .docx, the last render's lint report, and
a Look menu plus an accent picker (the preset swatches, or any color from the
picker or a hex field). A pick in the tab is written into the front matter of
the target's <stem>.md (`theme:` / `accent:`) and re-rendered by this server
with the same page count and .docx setting as the last render, so the agent's
next `render.py` run keeps the person's choice.

The page polls /<slug>/status.json every two seconds and swaps the page images
the moment a render writes new ones, so the tab keeps itself current. Never
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
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from render import ACCENTS, FRONT_RE, THEMES  # noqa: E402  (the renderer next to this file)

RENDER = os.path.join(HERE, "render.py")
RENDER_LOCK = threading.Lock()
ROOT = "/workspace/resume/targets"
PAGE_RE = re.compile(r"-(\d+)\.png$")
HEX_RE = re.compile(r"^#[0-9a-f]{6}$")
THEME_LABELS = {
    "modern": "Modern · sans, clean",
    "classic": "Classic · serif, centered",
    "compact": "Compact · dense, two pages",
    "editorial": "Editorial · serif display name",
    "warm": "Warm · serif body",
    "technical": "Technical · mono headings",
}

VIEWER = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { color-scheme: light; }
  html, body { margin: 0; background: #e5e7eb; color: #111827;
    font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  header { position: sticky; top: 0; z-index: 2; background: #fff; border-bottom: 1px solid #d1d5db;
    padding: 8px 16px; display: flex; flex-wrap: wrap; align-items: center; gap: 8px 18px; }
  header h1 { font-size: 15px; margin: 0; }
  header .status { color: #4b5563; }
  header nav { margin-left: auto; display: flex; gap: 12px; }
  header nav a { color: #1d4ed8; text-decoration: none; font-weight: 600; }
  .controls { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; flex-basis: 100%; }
  .controls label { display: inline-flex; align-items: center; gap: 6px; color: #374151; }
  .controls select { font: inherit; padding: 3px 6px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; }
  .swatches { display: inline-flex; align-items: center; gap: 6px; }
  .swatch { width: 20px; height: 20px; border-radius: 50%; border: 1px solid rgba(0,0,0,.25); padding: 0; cursor: pointer;
    box-shadow: 0 0 0 2px #fff; }
  .swatch.on { box-shadow: 0 0 0 2px #fff, 0 0 0 4px #1d4ed8; }
  .custom { display: inline-flex; align-items: center; gap: 6px; padding: 2px 6px 2px 2px; border: 1px solid transparent; border-radius: 8px; }
  .custom.on { border-color: #1d4ed8; }
  .custom input[type=color] { width: 26px; height: 26px; padding: 0; border: 1px solid #d1d5db; border-radius: 6px; background: none; cursor: pointer; }
  .custom input[type=text] { width: 5.5em; font: 13px ui-monospace, SFMono-Regular, Menlo, monospace; padding: 3px 6px;
    border: 1px solid #d1d5db; border-radius: 6px; }
  .custom input[type=text].bad { border-color: #b91c1c; }
  .controls[aria-busy=true] { opacity: .55; pointer-events: none; }
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
  section.report li.error { color: #b91c1c; }
</style></head>
<body>
<header>
  <h1 id="title">__TITLE__</h1>
  <span class="status" id="status">Waiting for the first render…</span>
  <nav id="links"></nav>
  <div class="controls" id="controls">
    <label>Look <select id="theme" aria-label="Theme"></select></label>
    <label>Accent <span class="swatches" id="swatches"></span></label>
    <span class="custom" id="custom" title="Custom accent">
      <input type="color" id="colorPick" aria-label="Pick a custom accent color">
      <input type="text" id="hex" placeholder="#1f4e79" maxlength="7" spellcheck="false" aria-label="Accent as hex">
    </span>
  </div>
</header>
<main>
  <div id="pages"><div class="empty">Waiting for the first render…</div></div>
  <section class="report" id="report" hidden></section>
</main>
<script>
(function () {
  const META = __META__;
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  let last = null;
  let busy = false;
  let hexDirty = false;
  let lastError = null;
  const current = { theme: null, accent: null };

  const themeSel = $("theme");
  META.themes.forEach((t) => {
    const o = document.createElement("option");
    o.value = t; o.textContent = META.labels[t] || t;
    themeSel.appendChild(o);
  });
  themeSel.addEventListener("change", () => apply({ theme: themeSel.value }));

  const sw = $("swatches");
  Object.entries(META.presets).forEach(([name, hex]) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "swatch"; b.style.background = hex;
    b.title = name; b.dataset.hex = hex.toLowerCase();
    b.setAttribute("aria-label", name + " accent");
    b.addEventListener("click", () => apply({ accent: name }));
    sw.appendChild(b);
  });

  const colorPick = $("colorPick");
  const hexIn = $("hex");
  colorPick.addEventListener("input", () => { hexIn.value = colorPick.value; hexIn.classList.remove("bad"); hexDirty = true; });
  colorPick.addEventListener("change", () => { hexIn.value = colorPick.value; hexDirty = false; apply({ accent: colorPick.value }); });
  hexIn.addEventListener("input", () => { hexDirty = true; hexIn.classList.remove("bad"); });
  hexIn.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); commitHex(); } });
  hexIn.addEventListener("blur", commitHex);
  function commitHex() {
    let v = hexIn.value.trim().toLowerCase();
    if (v && !v.startsWith("#")) v = "#" + v;
    if (/^#[0-9a-f]{3}$/.test(v)) v = "#" + v[1] + v[1] + v[2] + v[2] + v[3] + v[3];
    if (/^#[0-9a-f]{6}$/.test(v)) {
      hexIn.value = v; colorPick.value = v; hexIn.classList.remove("bad"); hexDirty = false;
      if (v !== (current.accent || "").toLowerCase()) apply({ accent: v });
    } else if (v) {
      hexIn.classList.add("bad");
    } else {
      hexDirty = false;
    }
  }

  async function apply(change) {
    if (busy) return;
    busy = true;
    $("controls").setAttribute("aria-busy", "true");
    $("status").textContent = "Rendering…";
    try {
      const res = await fetch("render", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(change) });
      const out = await res.json();
      lastError = out.ok ? null : (out.error || "render failed");
    } catch (e) {
      lastError = String(e);
    }
    busy = false;
    $("controls").removeAttribute("aria-busy");
    last = null; // force the next poll to redraw, so an error shows even when nothing changed
  }

  function syncControls(r) {
    current.theme = r.theme || null;
    current.accent = r.accent || null;
    if (r.theme && themeSel.value !== r.theme) themeSel.value = r.theme;
    const hex = (r.accent || "").toLowerCase();
    let matched = false;
    sw.querySelectorAll(".swatch").forEach((b) => { const on = b.dataset.hex === hex; b.classList.toggle("on", on); if (on) matched = true; });
    $("custom").classList.toggle("on", !!hex && !matched);
    if (!hexDirty) {
      hexIn.value = hex;
      if (/^#[0-9a-f]{6}$/.test(hex)) colorPick.value = hex;
    }
  }

  function render(s) {
    const r = s.report || {};
    const pages = s.pages || [];
    const parts = [];
    if (pages.length) parts.push(`${pages.length} page${pages.length === 1 ? "" : "s"}`);
    if (r.theme) parts.push(r.theme);
    if (r.paper) parts.push(r.paper);
    if (r.scale && r.scale !== 1) parts.push(`type at ${Math.round(r.scale * 100)}%`);
    if (r.rendered_at) parts.push(`rendered ${new Date(r.rendered_at).toLocaleTimeString()}`);
    if (!busy) $("status").textContent = parts.length ? parts.join(" · ") : "Waiting for the first render…";
    if (r.name) { $("title").textContent = r.name; document.title = r.name + " — preview"; }
    const links = [];
    if (s.pdf) links.push(`<a href="${esc(s.pdf)}?v=${esc(s.updated)}" download>Download PDF</a>`);
    if (s.docx) links.push(`<a href="${esc(s.docx)}?v=${esc(s.updated)}" download>Word</a>`);
    $("links").innerHTML = links.join("");
    syncControls(r);
    const el = $("pages");
    if (!pages.length) {
      el.innerHTML = '<div class="empty">Waiting for the first render…</div>';
    } else {
      el.innerHTML = pages.map((p, i) =>
        `<figure><img src="${esc(p.name)}?v=${p.mtime}" alt="Page ${i + 1}"><figcaption>Page ${i + 1} of ${pages.length}</figcaption></figure>`
      ).join("");
    }
    const rep = $("report");
    const items = [];
    if (lastError) items.push(`<li class="error">${esc(lastError)}</li>`);
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


def set_front_matter(text, updates):
    """Return `text` with the given front-matter keys set, the body untouched."""
    m = FRONT_RE.match(text)
    lines = m.group(1).splitlines() if m else []
    body = text[m.end():] if m else text
    out = []
    seen = set()
    for line in lines:
        key = line.split(":", 1)[0].strip().lower() if ":" in line else None
        if key in updates:
            out.append(f"{key}: {updates[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}: {value}")
    return "---\n" + "\n".join(out) + "\n---\n" + body.lstrip("\n")


def rerender(folder, slug, updates):
    """Write the front-matter changes and run render.py the way the last render ran."""
    status = target_status(folder, slug)
    stem = status["stem"] or "resume"
    source = os.path.join(folder, f"{stem}.md")
    if not os.path.isfile(source):
        candidates = [p for p in glob.glob(os.path.join(folder, "*.md")) if not p.endswith(".docx.md")]
        if len(candidates) != 1:
            return {"ok": False, "error": f"no {stem}.md in {slug}/ to re-render"}
        source = candidates[0]
    with open(source, encoding="utf-8") as fh:
        text = fh.read()
    with open(source, "w", encoding="utf-8") as fh:
        fh.write(set_front_matter(text, updates))
    report = status["report"] or {}
    cmd = [sys.executable, RENDER, source, "--out", folder]
    if report.get("target_pages"):
        cmd += ["--pages", str(report["target_pages"])]
    if report.get("docx"):
        cmd.append("--docx")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "render timed out"}
    tail = (proc.stdout + proc.stderr)[-1500:]
    if proc.returncode != 0:
        return {"ok": False, "error": tail.strip() or f"render exited {proc.returncode}"}
    return {"ok": True, "output": tail}


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

    def send_json(self, status, payload):
        self.send_bytes(status, json.dumps(payload).encode("utf-8"), "application/json")

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
            meta = {"slug": slug, "themes": list(THEMES), "labels": THEME_LABELS, "presets": ACCENTS}
            page = VIEWER.replace("__TITLE__", html.escape(slug)).replace("__META__", json.dumps(meta))
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

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        parts = [p for p in path.split("/") if p]
        if len(parts) != 2 or parts[1] != "render" or not safe_slug(parts[0]):
            return self.send_bytes(404, b"not found", "text/plain")
        folder = os.path.join(self.root, parts[0])
        if not os.path.isdir(folder):
            return self.send_bytes(404, b"no such target", "text/plain")
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("not an object")
        except (ValueError, TypeError):
            return self.send_json(400, {"ok": False, "error": "the body must be a JSON object"})
        updates = {}
        theme = payload.get("theme")
        if theme is not None:
            if theme not in THEMES:
                return self.send_json(400, {"ok": False, "error": f"unknown theme {theme!r}"})
            updates["theme"] = theme
        accent = payload.get("accent")
        if accent is not None:
            accent = str(accent).strip().lower()
            if accent in ACCENTS:
                updates["accent"] = accent
            elif HEX_RE.match(accent):
                updates["accent"] = f'"{accent}"'
            else:
                return self.send_json(400, {"ok": False, "error": "accent must be a preset name or #rrggbb"})
        if not updates:
            return self.send_json(400, {"ok": False, "error": "nothing to change"})
        if not RENDER_LOCK.acquire(blocking=False):
            return self.send_json(409, {"ok": False, "error": "a render is already running; try again in a moment"})
        try:
            result = rerender(folder, parts[0], updates)
        finally:
            RENDER_LOCK.release()
        return self.send_json(200 if result.get("ok") else 500, result)

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
