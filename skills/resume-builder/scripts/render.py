#!/usr/bin/env python3
"""render.py — turn a resume written in the Resume Builder Markdown dialect
into a print-quality PDF (plus preview PNGs, an ATS text check, and an
optional .docx).

usage:
  python3 render.py resume.md [--out DIR] [--theme classic|modern|compact]
                    [--paper letter|a4] [--pages N] [--accent '#1f4e79']
                    [--docx] [--html-only] [--check] [--dpi 110]

The same options can live in optional front matter at the top of the file;
CLI flags override it:

  ---
  theme: modern
  paper: letter
  pages: 1
  accent: "#1f4e79"
  ---

The dialect (see ../templates/example.md for a complete resume):

  # Full Name                                   -> the name (required, first H1)
  Headline line                                 -> optional one-line positioning
  City, ST · phone · email · linkedin.com/in/x  -> the contact line (has @ or a URL)
  ## Section                                    -> Summary, Experience, Education, Skills, ...
  ### Title | Organization | Location | Dates   -> an entry; empty fields may be left out,
                                                   the LAST field is the dates when it
                                                   contains a year or "Present"
  #### Role | Dates                             -> a sub-entry (promotions inside one company)
  - bullet                                      -> an accomplishment
  paragraph text                                -> prose (Summary, "Earlier career" lines)
  **bold**, *italic*, `code`, [text](url)       -> inline formatting

Outputs, in --out (default: next to the input):
  <stem>.html    the page that was printed
  <stem>.pdf     the resume
  <stem>-1.png   preview of page 1 (-2, -3 when they exist)
  <stem>.docx    only with --docx (needs pandoc)

Exit status is 0 even when the lint prints warnings; it is non-zero only when
the file cannot be parsed or a tool is missing.
"""

import argparse
import glob
import html
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
THEMES = ("classic", "modern", "compact")
PAPERS = {"letter": "letter", "a4": "A4"}
FIT_SCALES = (1.0, 0.97, 0.94, 0.92)  # 0.92 of a 10.5pt base is ~9.7pt: the floor

# ----------------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------------

FRONT_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", re.S)
DATE_RE = re.compile(r"\b(19|20)\d{2}\b|\bpresent\b|\bcurrent\b|\bexpected\b|\bnow\b|\btoday\b", re.I)
CONTACT_SPLIT_RE = re.compile(r"\s*[·•|]\s*")
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
URLISH_RE = re.compile(r"^(https?://)?([\w-]+\.)+[a-z]{2,}(/\S*)?$", re.I)
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")
MARKER_RE = re.compile(r"\[(needs number|needs date|verify|todo|tbd|unverified)[^\]]*\]", re.I)


def parse_front_matter(text):
    m = FRONT_RE.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            key, value = line.split(":", 1)
            meta[key.strip().lower()] = value.strip().strip("\"'")
    return meta, text[m.end():]


def looks_like_contact(paragraph):
    if "@" in paragraph or "http" in paragraph or "linkedin" in paragraph.lower():
        return True
    return bool(PHONE_RE.search(paragraph))


def parse_entry_heading(text):
    fields = [f.strip() for f in text.split("|")]
    title = fields[0] if fields else ""
    rest = [f for f in fields[1:]]
    dates = ""
    if rest and DATE_RE.search(rest[-1]):
        dates = rest.pop()
    rest = [f for f in rest if f]
    org = rest[0] if rest else ""
    location = " · ".join(rest[1:]) if len(rest) > 1 else ""
    return {"title": title, "org": org, "location": location, "dates": dates, "blocks": [], "subs": []}


def new_section(title):
    return {"title": title, "blocks": [], "entries": []}


def parse_body(text):
    """Returns the resume model: name, headline, contact, sections."""
    model = {"name": "", "headline": "", "contact": [], "sections": [], "pre": []}
    section = None
    entry = None
    sub = None
    para = []
    list_stack = []  # stack of (indent, items) for nested bullets

    def container():
        if sub is not None:
            return sub["blocks"]
        if entry is not None:
            return entry["blocks"]
        if section is not None:
            return section["blocks"]
        return model["pre"]

    def flush_para():
        nonlocal para
        if para:
            container().append({"type": "p", "text": " ".join(s.strip() for s in para)})
            para = []

    def flush_list():
        nonlocal list_stack
        if list_stack:
            root = list_stack[0][1]
            container().append({"type": "ul", "items": root})
            list_stack = []

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        bullet = re.match(r"^(\s*)[-*+]\s+(.*)$", line)
        if bullet:
            flush_para()
            indent = len(bullet.group(1).expandtabs(4))
            item = {"text": bullet.group(2).strip(), "children": []}
            if not list_stack:
                list_stack = [(indent, [item])]
            else:
                while len(list_stack) > 1 and indent < list_stack[-1][0]:
                    list_stack.pop()
                if indent > list_stack[-1][0]:
                    parent = list_stack[-1][1][-1]
                    parent["children"].append(item)
                    list_stack.append((indent, parent["children"]))
                else:
                    list_stack[-1][1].append(item)
            continue
        if not stripped:
            flush_para()
            flush_list()
            continue
        if stripped.startswith("#"):
            flush_para()
            flush_list()
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped[level:].strip()
            if level == 1 and not model["name"]:
                model["name"] = title
            elif level <= 2:
                section = new_section(title)
                model["sections"].append(section)
                entry = None
                sub = None
            elif level == 3:
                if section is None:
                    section = new_section("")
                    model["sections"].append(section)
                entry = parse_entry_heading(title)
                section["entries"].append(entry)
                sub = None
            else:
                if entry is None:
                    if section is None:
                        section = new_section("")
                        model["sections"].append(section)
                    entry = parse_entry_heading(title)
                    section["entries"].append(entry)
                else:
                    sub = parse_entry_heading(title)
                    entry["subs"].append(sub)
            continue
        if stripped == "---":
            flush_para()
            flush_list()
            continue
        if list_stack and line.startswith(" ") and not bullet:
            # continuation line of a bullet
            list_stack[-1][1][-1]["text"] += " " + stripped
            continue
        flush_list()
        para.append(stripped)
        if section is None:
            # Header lines (headline, contact) are one paragraph each, no blank line needed.
            flush_para()
    flush_para()
    flush_list()

    for block in model["pre"]:
        if block["type"] != "p":
            continue
        if not model["contact"] and looks_like_contact(block["text"]):
            model["contact"] = [c for c in CONTACT_SPLIT_RE.split(block["text"]) if c]
        elif not model["headline"]:
            model["headline"] = block["text"]
    if not model["name"]:
        sys.exit("render.py: the resume needs a name as its first '# ' heading")
    return model


# ----------------------------------------------------------------------------
# Lint — advice, never a gate
# ----------------------------------------------------------------------------

WEAK_OPENERS = (
    "responsible for", "helped", "worked on", "assisted with", "participated in",
    "tasked with", "duties included", "in charge of", "involved in", "was part of",
)
FIRST_PERSON_RE = re.compile(r"\b(I|my|me|we|our)\b")
STANDARD_SECTIONS = (
    "summary", "experience", "education", "skills", "projects", "leadership",
    "activities", "publications", "awards", "certifications", "volunteering",
    "additional", "interests", "languages", "research", "teaching", "talks",
)


def iter_bullets(model):
    def walk_blocks(blocks, where):
        for block in blocks:
            if block["type"] == "ul":
                stack = list(block["items"])
                while stack:
                    item = stack.pop(0)
                    yield where, item["text"]
                    stack = item["children"] + stack

    for section in model["sections"]:
        yield from walk_blocks(section["blocks"], section["title"])
        for entry in section["entries"]:
            where = f"{section['title']} / {entry['title'] or entry['org']}"
            yield from walk_blocks(entry["blocks"], where)
            for sub in entry["subs"]:
                yield from walk_blocks(sub["blocks"], f"{where} / {sub['title']}")


def lint(model, raw_text):
    warnings = []
    infos = []
    if not any(EMAIL_RE.match(c.strip()) for c in model["contact"]):
        warnings.append("contact line has no email address")
    markers = MARKER_RE.findall(raw_text)
    if markers:
        warnings.append(f"{len(markers)} unresolved marker(s) such as [needs number] — resolve before delivery")
    bullets = list(iter_bullets(model))
    with_numbers = 0
    for where, text in bullets:
        lowered = text.lower().lstrip("*_ ")
        plain = re.sub(r"\*\*[^*]+\*\*\s*", "", lowered) if lowered.startswith("**") else lowered
        if any(plain.startswith(w) for w in WEAK_OPENERS):
            warnings.append(f"weak opener in {where}: \"{text[:70]}\"")
        if FIRST_PERSON_RE.search(text):
            warnings.append(f"first person in {where}: \"{text[:70]}\"")
        if len(text) > 230:
            warnings.append(f"bullet likely runs past two lines in {where} ({len(text)} chars)")
        if re.search(r"\d", text):
            with_numbers += 1
    if bullets:
        infos.append(f"{with_numbers}/{len(bullets)} bullets carry a number")
    for section in model["sections"]:
        title = section["title"].lower()
        if title and not any(s in title for s in STANDARD_SECTIONS):
            infos.append(f"section \"{section['title']}\" is not a standard heading; screeners parse standard ones best")
        for entry in section["entries"]:
            if entry["dates"] or entry["subs"]:
                continue
            if "experience" in title:
                warnings.append(f"no dates on \"{entry['title']}\" in {section['title']}")
            elif "education" in title:
                infos.append(f"no dates on \"{entry['title']}\" (fine past 15 years; otherwise add them)")
    return warnings, infos


# ----------------------------------------------------------------------------
# HTML
# ----------------------------------------------------------------------------


def inline(text):
    text = html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\((\S+?)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def contact_item(item):
    item = item.strip()
    if EMAIL_RE.match(item):
        return f'<a href="mailto:{html.escape(item)}">{html.escape(item)}</a>'
    if URLISH_RE.match(item) and "." in item:
        href = item if item.startswith("http") else f"https://{item}"
        shown = re.sub(r"^https?://(www\.)?", "", item).rstrip("/")
        return f'<a href="{html.escape(href)}">{html.escape(shown)}</a>'
    return inline(item)


def render_list(items):
    out = ["<ul>"]
    for item in items:
        out.append(f"<li>{inline(item['text'])}")
        if item["children"]:
            out.append(render_list(item["children"]))
        out.append("</li>")
    out.append("</ul>")
    return "".join(out)


def render_blocks(blocks):
    out = []
    for block in blocks:
        if block["type"] == "p":
            out.append(f"<p>{inline(block['text'])}</p>")
        elif block["type"] == "ul":
            out.append(render_list(block["items"]))
    return "".join(out)


def render_entry_head(entry, cls="entry-head"):
    main = []
    if entry["title"]:
        main.append(f'<span class="title">{inline(entry["title"])}</span>')
    if entry["org"]:
        main.append(f'<span class="org">{inline(entry["org"])}</span>')
    side = []
    if entry["location"]:
        side.append(f'<span class="loc">{inline(entry["location"])}</span>')
    if entry["dates"]:
        side.append(f'<span class="dates">{inline(entry["dates"])}</span>')
    return (
        f'<div class="{cls}"><div class="entry-main">{"".join(main)}</div>'
        f'<div class="entry-side">{"".join(side)}</div></div>'
    )


def render_entry(entry):
    out = ['<div class="entry">', render_entry_head(entry), render_blocks(entry["blocks"])]
    for sub in entry["subs"]:
        out.append('<div class="sub">')
        out.append(render_entry_head(sub, "entry-head sub-head"))
        out.append(render_blocks(sub["blocks"]))
        out.append("</div>")
    out.append("</div>")
    return "".join(out)


def section_class(title):
    lowered = title.lower()
    if any(k in lowered for k in ("skill", "technical", "competenc", "tools", "languages")):
        return "sec sec-skills"
    if "summary" in lowered or "profile" in lowered:
        return "sec sec-summary"
    return "sec"


def render_html(model, settings, css):
    parts = [
        "<!doctype html><html><head><meta charset=\"utf-8\">",
        f"<title>{html.escape(model['name'])} — Resume</title>",
        "<style>",
        css,
        f"@page {{ size: {PAPERS[settings['paper']]}; }}",
        f":root {{ --scale: {settings['scale']}; --accent: {settings['accent']}; }}",
        "</style></head><body>",
        '<header class="head">',
        f'<h1 class="name">{inline(model["name"])}</h1>',
    ]
    if model["headline"]:
        parts.append(f'<div class="headline">{inline(model["headline"])}</div>')
    if model["contact"]:
        items = [contact_item(c) for c in model["contact"]]
        parts.append('<div class="contact">' + '<span class="sep">·</span>'.join(f"<span>{i}</span>" for i in items) + "</div>")
    parts.append("</header>")
    for section in model["sections"]:
        parts.append(f'<section class="{section_class(section["title"])}">')
        if section["title"]:
            parts.append(f"<h2>{inline(section['title'])}</h2>")
        parts.append(render_blocks(section["blocks"]))
        for entry in section["entries"]:
            parts.append(render_entry(entry))
        parts.append("</section>")
    parts.append("</body></html>")
    return "".join(parts)


def load_css(theme):
    base = open(os.path.join(HERE, "themes", "base.css"), encoding="utf-8").read()
    skin = open(os.path.join(HERE, "themes", f"{theme}.css"), encoding="utf-8").read()
    return base + "\n" + skin


# ----------------------------------------------------------------------------
# PDF, previews, checks
# ----------------------------------------------------------------------------


def find_chrome():
    candidates = [
        os.environ.get("RESUME_CHROME"),
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome",
        "google-chrome-stable",
        "google-chrome",
        "chromium",
        "chromium-browser",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for c in candidates:
        if not c:
            continue
        found = c if os.path.isabs(c) and os.path.exists(c) else shutil.which(c)
        if found:
            return found
    sys.exit("render.py: no Chrome or Chromium found; set RESUME_CHROME=/path/to/chrome")


def print_pdf(chrome, html_path, pdf_path):
    """Print the HTML to PDF with headless Chrome.

    Chrome writes the whole PDF in one go once the page has rendered, and some
    builds (macOS with the Google updater attached) then never exit. So: wait
    for the file to appear and hold a stable size, give Chrome a moment to
    quit on its own, and kill the whole process group if it does not.
    """
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    with tempfile.TemporaryDirectory(prefix="resume-chrome-") as profile:
        cmd = [
            chrome,
            "--headless",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            "--use-mock-keychain",
            f"--user-data-dir={profile}",
            "--no-pdf-header-footer",
            "--virtual-time-budget=4000",
            f"--print-to-pdf={pdf_path}",
            f"file://{os.path.abspath(html_path)}",
        ]
        log_path = os.path.join(profile, "chrome.log")
        with open(log_path, "w") as log:
            proc = subprocess.Popen(cmd, stdout=log, stderr=log, start_new_session=True)
            deadline = time.time() + 120
            last_size = -1
            while time.time() < deadline:
                if proc.poll() is not None:
                    break
                size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
                if size > 0 and size == last_size:
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        pass
                    break
                last_size = size
                time.sleep(0.3)
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except OSError:
                    proc.kill()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
        if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
            with open(log_path, errors="replace") as log:
                tail = log.read()[-2000:]
            sys.exit(f"render.py: Chrome did not write {pdf_path}\n{tail}")


def page_count(pdf_path):
    try:
        from pypdf import PdfReader

        return len(PdfReader(pdf_path).pages)
    except Exception:
        out = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True).stdout
        m = re.search(r"Pages:\s+(\d+)", out)
        return int(m.group(1)) if m else -1


def previews(pdf_path, stem, pages, dpi):
    for old in glob.glob(f"{stem}-*.png"):
        os.remove(old)
    if not shutil.which("pdftoppm"):
        return []
    last = min(pages, 3) if pages > 0 else 3
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-f", "1", "-l", str(last), pdf_path, stem],
                   capture_output=True, text=True)
    return sorted(glob.glob(f"{stem}-*.png"))


def ats_check(pdf_path, model):
    if not shutil.which("pdftotext"):
        return ["pdftotext not installed; skipped the text-extraction check"]
    text = subprocess.run(["pdftotext", "-layout", pdf_path, "-"], capture_output=True, text=True).stdout
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    notes = []
    if not lines:
        return ["the PDF has NO extractable text — a screener would read nothing"]
    if not any(model["name"].lower() in l.lower() for l in lines[:3]):
        notes.append("the name is not in the first three extracted lines")
    lowered = text.lower()
    position = -1
    for section in model["sections"]:
        if not section["title"]:
            continue
        found = lowered.find(section["title"].lower(), position + 1)
        if found < 0:
            notes.append(f"section heading \"{section['title']}\" was not found in extracted text order")
        else:
            position = found
    if not notes:
        notes.append("extracted text reads in order: name first, then every section heading")
    return notes


def docx_markdown(model):
    out = [f"# {model['name']}", ""]
    if model["headline"]:
        out += [model["headline"], ""]
    if model["contact"]:
        out += [" · ".join(model["contact"]), ""]

    def blocks_md(blocks, indent=""):
        for block in blocks:
            if block["type"] == "p":
                out.append(f"{indent}{block['text']}")
                out.append("")
            elif block["type"] == "ul":
                def items_md(items, depth):
                    for item in items:
                        out.append(f"{'    ' * depth}- {item['text']}")
                        items_md(item["children"], depth + 1)
                items_md(block["items"], 0)
                out.append("")

    def entry_md(entry, level):
        head = f"**{entry['title']}**" if entry["title"] else ""
        if entry["org"]:
            head += f", {entry['org']}" if head else entry["org"]
        side = " · ".join(x for x in (entry["location"], entry["dates"]) if x)
        if side:
            head += f" — *{side}*"
        out.append(head)
        out.append("")
        blocks_md(entry["blocks"])
        for sub in entry["subs"]:
            entry_md(sub, level + 1)

    for section in model["sections"]:
        if section["title"]:
            out += [f"## {section['title']}", ""]
        blocks_md(section["blocks"])
        for entry in section["entries"]:
            entry_md(entry, 0)
    return "\n".join(out).rstrip() + "\n"


def write_docx(model, stem):
    if not shutil.which("pandoc"):
        return None, "pandoc not installed; no .docx written"
    md_path = f"{stem}.docx.md"
    docx_path = f"{stem}.docx"
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(docx_markdown(model))
    result = subprocess.run(["pandoc", md_path, "-f", "markdown", "-t", "docx", "-o", docx_path],
                            capture_output=True, text=True)
    os.remove(md_path)
    if result.returncode != 0:
        return None, f"pandoc failed: {result.stderr[-500:]}"
    return docx_path, None


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("--out", help="output directory (default: next to the source)")
    ap.add_argument("--theme", choices=THEMES)
    ap.add_argument("--paper", choices=sorted(PAPERS))
    ap.add_argument("--pages", type=int, help="fit to this many pages by scaling type down to ~9.7pt")
    ap.add_argument("--accent", help="CSS color for the name and rules, e.g. '#1f4e79'")
    ap.add_argument("--docx", action="store_true", help="also write a .docx through pandoc")
    ap.add_argument("--html-only", action="store_true", help="write the HTML and stop")
    ap.add_argument("--check", action="store_true", help="parse and lint only; write nothing")
    ap.add_argument("--dpi", type=int, default=110, help="preview PNG resolution")
    args = ap.parse_args()

    with open(args.source, encoding="utf-8") as fh:
        raw = fh.read()
    meta, body = parse_front_matter(raw)
    model = parse_body(body)

    settings = {
        "theme": args.theme or meta.get("theme", "modern"),
        "paper": (args.paper or meta.get("paper", "letter")).lower(),
        "pages": args.pages if args.pages is not None else (int(meta["pages"]) if meta.get("pages", "").isdigit() else None),
        "accent": args.accent or meta.get("accent") or "",
        "scale": 1.0,
    }
    if settings["theme"] not in THEMES:
        sys.exit(f"render.py: unknown theme {settings['theme']!r}; use one of {', '.join(THEMES)}")
    if settings["paper"] not in PAPERS:
        sys.exit(f"render.py: unknown paper {settings['paper']!r}; use letter or a4")
    if not settings["accent"]:
        settings["accent"] = "#1f2937" if settings["theme"] != "classic" else "#111111"

    warnings, infos = lint(model, body)
    print(f"parsed: {model['name']} — {len(model['sections'])} sections, "
          f"{sum(len(s['entries']) for s in model['sections'])} entries, "
          f"{len(list(iter_bullets(model)))} bullets")
    for note in infos:
        print(f"  note: {note}")
    for warning in warnings:
        print(f"  warn: {warning}")
    if args.check:
        return

    out_dir = args.out or os.path.dirname(os.path.abspath(args.source))
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.join(out_dir, os.path.splitext(os.path.basename(args.source))[0])
    html_path = f"{stem}.html"
    pdf_path = f"{stem}.pdf"
    css = load_css(settings["theme"])

    def write_html(scale):
        settings["scale"] = scale
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(render_html(model, settings, css))

    write_html(1.0)
    if args.html_only:
        print(f"html: {html_path}")
        return

    chrome = find_chrome()
    print_pdf(chrome, html_path, pdf_path)
    pages = page_count(pdf_path)
    target = settings["pages"]
    if target and pages > target:
        for scale in FIT_SCALES[1:]:
            write_html(scale)
            print_pdf(chrome, html_path, pdf_path)
            pages = page_count(pdf_path)
            if pages <= target:
                break
        if pages > target:
            print(f"  warn: still {pages} pages at the smallest readable size (scale {settings['scale']}). "
                  "Cut content instead of shrinking further.")
    print(f"pdf: {pdf_path} ({pages} page{'s' if pages != 1 else ''}, theme {settings['theme']}, "
          f"scale {settings['scale']})")
    for png in previews(pdf_path, stem, pages, args.dpi):
        print(f"preview: {png}")
    for note in ats_check(pdf_path, model):
        print(f"  text check: {note}")
    if args.docx:
        docx_path, error = write_docx(model, stem)
        print(f"docx: {docx_path}" if docx_path else f"  warn: {error}")


if __name__ == "__main__":
    main()
