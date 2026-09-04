#!/usr/bin/env python3
"""
Build one chapter PDF from markdown. Runs on the agent's computer.

Pipeline:
  1. Read <chapter_dir>/chapter.md (YAML frontmatter + body)
  2. Fenced ```mermaid blocks -> PNG via mmdc (cached by content hash)
  3. $...$ and $$...$$ math -> HTML via the katex CLI (no JS at PDF time)
  4. pandoc: markdown -> HTML5 body, wrapped in our own template
  5. weasyprint: HTML -> PDF

Usage (from the book project dir, /workspace/books/<slug>):
  python3 /.skills/book-pdf/scripts/build_chapter.py chapters/01-intro
Env:
  BOOK_THEME=theme/reading.css | theme/print.css   (default reading)
  BOOK_MATH_MODE=katex|plain   BOOK_ASCII_SAFE=1   BOOK_OUTPUT_SUFFIX=-print
"""
import hashlib
import html as html_lib
import os
import re
import subprocess
import sys
from pathlib import Path

# ROOT is the BOOK PROJECT (cwd), not the skill folder: scripts live in
# /.skills/book-pdf/scripts, the book lives in /workspace/books/<slug>.
ROOT = Path.cwd()
SKILL = Path(__file__).resolve().parent.parent
THEME = Path(os.environ.get("BOOK_THEME", ROOT / "theme" / "reading.css")).resolve()
BUILD = ROOT / "build"
BUILD.mkdir(exist_ok=True)


def _katex_css() -> str:
    """katex.min.css from the global npm root (setup.sh installs katex there)."""
    env = os.environ.get("KATEX_CSS")
    if env:
        return env
    try:
        root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        root = "/usr/local/lib/node_modules"
    return f"{root}/katex/dist/katex.min.css"


KATEX_CSS = _katex_css()
PUPPETEER_CONFIG = SKILL / "scripts" / "puppeteer-config.json"
MERMAID_CONFIG = Path(os.environ.get("BOOK_MERMAID_CONFIG", SKILL / "scripts" / "mermaid-config.json"))
OUTPUT_SUFFIX = os.environ.get("BOOK_OUTPUT_SUFFIX", "")
MERMAID_WIDTH = os.environ.get("BOOK_MERMAID_WIDTH", "2400")
MERMAID_SCALE = os.environ.get("BOOK_MERMAID_SCALE", "2")
MATH_MODE = os.environ.get("BOOK_MATH_MODE", "katex")
ASCII_SAFE = os.environ.get("BOOK_ASCII_SAFE", "") == "1"
STRIP_MATHML = os.environ.get("BOOK_STRIP_MATHML", "") == "1"


def ascii_sanitize(text: str) -> str:
    replacements = {
        "—": "-",
        "–": "-",
        "−": "-",
        "→": "->",
        "←": "<-",
        "×": "x",
        "≤": "<=",
        "≥": ">=",
        "≈": "~",
        "∆": "Delta",
        "±": "+/-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "…": "...",
        "\u00a0": " ",
    }
    return "".join(replacements.get(ch, ch if ord(ch) < 128 else "?") for ch in text)


def render_math_blocks(md: str) -> str:
    """Pre-render $$...$$ and $...$ math via katex CLI; replace with raw HTML.
    Avoids dependency on JS in the PDF renderer."""

    def render(expr: str, display: bool) -> str:
        if MATH_MODE == "plain":
            cleaned = ascii_sanitize(expr)
            cleaned = re.sub(r"\\text\{([^{}]+)\}", r"\1", cleaned)
            cleaned = cleaned.replace("\\cdot", "*").replace("\\times", "x")
            cleaned = cleaned.replace("\\Delta", "Delta").replace("\\approx", "~")
            cleaned = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", cleaned)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            tag = "div" if display else "span"
            cls = "math-display plain-math" if display else "plain-math"
            return f'<{tag} class="{cls}">{html_lib.escape(cleaned)}</{tag}>'

        flags = ["-t"]  # render errors instead of throwing
        if display:
            flags.append("-d")
        proc = subprocess.run(
            ["katex"] + flags,
            input=expr, text=True, capture_output=True,
        )
        if proc.returncode != 0:
            return f"<code>{expr}</code>"
        out = proc.stdout.strip()
        if STRIP_MATHML:
            out = re.sub(r'<span class="katex-mathml">.*?</span>', "", out, flags=re.DOTALL)
        if display:
            return f'<div class="math-display">{out}</div>'
        return out

    # display math first ($$...$$). Use a non-greedy match across multiple lines.
    md = re.sub(
        r"\$\$(.+?)\$\$",
        lambda m: render(m.group(1).strip(), display=True),
        md,
        flags=re.DOTALL,
    )

    # inline math: single $...$ not preceded/followed by $ or \, not crossing newlines.
    # Skip code spans (backticks) using a tokenizer-style pass.
    out_parts: list[str] = []
    i = 0
    while i < len(md):
        # skip past backtick-fenced code spans
        if md[i] == "`":
            j = md.find("`", i + 1)
            if j == -1:
                out_parts.append(md[i:])
                break
            out_parts.append(md[i:j + 1])
            i = j + 1
            continue
        # skip fenced code blocks (```...```)
        if md.startswith("```", i):
            j = md.find("```", i + 3)
            if j == -1:
                out_parts.append(md[i:])
                break
            out_parts.append(md[i:j + 3])
            i = j + 3
            continue
        if md[i] == "$" and (i == 0 or md[i - 1] != "\\"):
            # pandoc rules: opening $ must be followed by non-space;
            # closing $ must be preceded by non-space and not followed by a digit;
            # expression has no $ inside, doesn't cross blank lines.
            if i + 1 >= len(md) or md[i + 1] in (" ", "\t", "\n") or md[i + 1].isdigit():
                out_parts.append(md[i])
                i += 1
                continue
            j = i + 1
            found = -1
            while j < len(md):
                if md[j] == "\n" and j + 1 < len(md) and md[j + 1] == "\n":
                    break
                if md[j] == "$" and md[j - 1] not in (" ", "\t", "\n", "\\"):
                    after = md[j + 1] if j + 1 < len(md) else ""
                    if not after.isdigit():
                        found = j
                        break
                j += 1
            if found != -1:
                expr = md[i + 1:found]
                if expr and "\n\n" not in expr:
                    out_parts.append(render(expr, display=False))
                    i = found + 1
                    continue
        out_parts.append(md[i])
        i += 1
    return "".join(out_parts)


def render_mermaid_blocks(md: str, chapter_dir: Path) -> str:
    """Replace ```mermaid ... ``` fenced blocks with <div class='figure'><img ...></div>.
    Caches rendered SVGs by content hash."""
    diagrams = chapter_dir / "diagrams"
    diagrams.mkdir(exist_ok=True)

    pattern = re.compile(
        r"^```mermaid\s*(?:\{([^}]*)\})?\s*\n(.*?)\n```\s*$",
        re.DOTALL | re.MULTILINE,
    )

    def replace(m: re.Match) -> str:
        attrs = (m.group(1) or "").strip()
        body = m.group(2)
        caption_match = re.search(r'caption="([^"]+)"', attrs)
        caption = caption_match.group(1) if caption_match else ""
        h = hashlib.sha1(f"{body}|w={MERMAID_WIDTH}|s={MERMAID_SCALE}".encode("utf-8")).hexdigest()[:12]
        png_path = diagrams / f"diagram_{h}.png"
        if not png_path.exists():
            mmd_path = diagrams / f"diagram_{h}.mmd"
            mmd_path.write_text(body)
            print(f"  [mermaid] rendering {png_path.name}")
            try:
                subprocess.run(
                    [
                        "mmdc", "-i", str(mmd_path), "-o", str(png_path),
                        "-b", "white",
                        "-c", str(MERMAID_CONFIG),
                        "-p", str(PUPPETEER_CONFIG),
                        "-w", MERMAID_WIDTH, "-s", MERMAID_SCALE,
                        "--quiet",
                    ],
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError as e:
                print(f"  [mermaid] FAIL on diagram {h}: {e.stderr.decode()[:300]}")
                return f'<div class="figure"><pre>{body}</pre></div>'
        cap = f'<div class="caption">{caption}</div>' if caption else ""
        return (
            f'<div class="figure">'
            f'<img src="file://{png_path}" alt="diagram"/>'
            f'{cap}</div>'
        )

    return pattern.sub(replace, md)


def parse_frontmatter(md: str) -> tuple[dict, str]:
    """Pull a simple YAML frontmatter block out of md. Returns (meta, body)."""
    meta = {}
    if md.startswith("---\n"):
        end = md.find("\n---\n", 4)
        if end != -1:
            yaml_block = md[4:end]
            for line in yaml_block.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip().strip('"').strip("'")
            md = md[end + 5:]
    return meta, md


def md_to_html(md: str, chapter_dir: Path, out_html: Path, meta: dict) -> None:
    """Convert markdown to HTML, wrap in our own template (no pandoc title block)."""
    css_rel = os.path.relpath(THEME, out_html.parent)

    cmd = [
        "pandoc",
        "-f", "markdown+raw_html+fenced_divs+header_attributes+table_attributes+pipe_tables+grid_tables+footnotes+inline_notes+smart+yaml_metadata_block-tex_math_dollars",
        "-t", "html5",
        "--section-divs",
        "--wrap=preserve",
        f"--resource-path={chapter_dir}",
    ]
    proc = subprocess.run(cmd, input=md, text=True, capture_output=True)
    if proc.returncode != 0:
        print("pandoc stderr:", proc.stderr)
        raise SystemExit(proc.returncode)
    body = proc.stdout
    if ASCII_SAFE:
        body = ascii_sanitize(body)

    title = meta.get("title", "Chapter")
    chap_num = meta.get("chapter-num", "1")
    book_title = meta.get("book-title", "Custom Book")
    # subtract 1 so that the first counter-increment lands on the desired number
    chap_seed = str(int(chap_num) - 1)

    katex_link = "" if MATH_MODE == "plain" else f'<link rel="stylesheet" href="file://{KATEX_CSS}">'
    title_joiner = " - " if ASCII_SAFE else " — "

    # role: front | chapter | back (frontmatter). Front and back matter get no
    # "Chapter N" kicker. Falls back to chapter-num 0 = front.
    role = meta.get("role") or ("front" if chap_num in ("0", "00") else "chapter")
    body_class = role if role in ("front", "chapter", "back") else "chapter"
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
{katex_link}
<link rel="stylesheet" href="{css_rel}">
<style>
  body {{ counter-reset: chapter {chap_seed}; string-set: book-title "{book_title}{title_joiner}{title}"; }}
  .math-display {{ margin: 0.10in 0; text-align: center; page-break-inside: avoid; }}
  .plain-math {{ font-family: "Times New Roman", "Arial Unicode MS", serif; font-style: italic; }}
  .katex {{ font-size: 1em !important; }}
  .katex-display {{ margin: 0.10in 0 !important; }}
</style>
</head>
<body class="{body_class}">
{body}
</body>
</html>
"""
    out_html.write_text(html)


def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    print(f"  [weasyprint] {html_path.name} -> {pdf_path.name}")
    cmd = ["weasyprint", str(html_path), str(pdf_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print("weasyprint stderr:", proc.stderr)
        raise SystemExit(proc.returncode)
    if proc.stderr:
        # WeasyPrint warns to stderr; surface but don't fail
        for line in proc.stderr.splitlines():
            if line.strip():
                print(f"  [weasyprint warn] {line}")


def main():
    if len(sys.argv) < 2:
        print("usage: build_chapter.py <chapter_dir>")
        sys.exit(1)
    chapter_dir = Path(sys.argv[1]).resolve()
    md_path = chapter_dir / "chapter.md"
    if not md_path.exists():
        print(f"no chapter.md in {chapter_dir}")
        sys.exit(1)

    print(f"== Building {chapter_dir.name} ==")
    md_raw = md_path.read_text()
    meta, md = parse_frontmatter(md_raw)
    print(f"  meta: {meta}")

    print("  [1/4] rendering mermaid diagrams")
    md = render_mermaid_blocks(md, chapter_dir)

    print("  [2/4] rendering math (katex)")
    md = render_math_blocks(md)

    out_html = BUILD / f"{chapter_dir.name}{OUTPUT_SUFFIX}.html"
    print(f"  [3/4] markdown -> html")
    md_to_html(md, chapter_dir, out_html, meta)

    out_pdf = BUILD / f"{chapter_dir.name}{OUTPUT_SUFFIX}.pdf"
    print(f"  [4/4] html -> pdf")
    html_to_pdf(out_html, out_pdf)

    size_kb = out_pdf.stat().st_size / 1024
    print(f"\n  done: {out_pdf}  ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
