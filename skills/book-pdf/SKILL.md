---
name: Book PDF
description: Write and typeset a book-length PDF (40–400 pages) on any subject, entirely on this computer: markdown chapters with Mermaid diagrams, KaTeX math, callouts and tables, rendered through pandoc and WeasyPrint into one PDF with chapter openers, running headers, figure numbers and a glossary. Two themes, a letter-size reading PDF and a 6×9 B&W print interior. Use when the user asks for a book, a long primer, a custom textbook or reference, or "turn this into a proper PDF I can read on paper". Not for short docs (use a doc artifact), slides, or compiling existing PDFs.
---

# Book PDF

You are writing a real book and typesetting it. The reader is smart, fast, and
new to the subject. The output is one PDF they open, print, or send. The bar:
it should look like a trade nonfiction book, not a report, and read like one.

The pipeline runs here, on this computer, with tools that are already on the
image plus three installs from `scripts/setup.sh`. Nothing leaves the machine.

```
ask_question ──► outline + FACTS.md ──► one worker per chapter (forks)
      └──► build_all.sh: mermaid→PNG, katex→HTML, pandoc→HTML, weasyprint→PDF, qpdf merge
      └──► preview.sh pages ──► fix ──► deliver  sandbox:/workspace/books/<slug>/build/book.pdf
```

Scripts: `/.skills/book-pdf/scripts/`. Themes: `/.skills/book-pdf/theme/`.
Do not rewrite them. Your work is the outline, `FACTS.md`, and the chapters.

## Step 0 — File the task, then ask

`update_task` (InProgress), then one `ask_question` card. Skip anything the
request or a file in `/workspace` already answers.

1. **Subject and angle** `long_text`: "What should the book teach, and from
   what angle? Paste notes or name a file in /workspace if you have one."
2. **Reader** `choice`: Smart newcomer to the field / Practitioner who wants
   depth / Student preparing for an exam / A team that needs a shared primer.
3. **Length** `choice`: Short primer (~40 pages) / Standard (~120 pages) /
   Full book (~200 pages) / Big reference (300+ pages).
4. **Format** `choice`: Reading PDF, letter size, warm background (default) /
   Print interior, 6×9, black and white / Both.
5. **Numbers and sources** `choice`: Real figures with named source classes
   (IEA, 10-K, IPCC, textbooks) / Illustrative numbers are fine.
6. **Must include / must avoid** `text`, optional.

End your turn. Answers reopen the task.

## Step 1 — Set up and scaffold

```bash
bash /.skills/book-pdf/scripts/setup.sh                       # once per machine, ~2 min
bash /.skills/book-pdf/scripts/new_book.sh <slug> "<Book Title>"   # → /workspace/books/<slug>
cd /workspace/books/<slug>
```

Setup adds WeasyPrint (pip), KaTeX and mermaid-cli (npm, pointed at the
installed Chrome so nothing large downloads). pandoc, qpdf, poppler and the
Noto and Liberation fonts are already on the image. It ends with a smoke
render of one Mermaid diagram; if that fails, read the error before writing
a word.

Run setup **before forking workers** so every fork inherits it, and note the
project path in `/workspace/.orgorg/README-fork.md`.

## Step 2 — Outline and the shared fact sheet

Two files decide whether twelve parallel chapters read as one book.

**`outline.md`**: the chapter list with, per chapter: number, slug, title,
one-line thesis, the 3–6 parts (these become `##` headings), the diagrams it
must contain, the worked examples, and what the reader can do after it. Front
matter is chapter 00 (`role: front`); the glossary and further reading are the
last chapter (`role: back`). Page budget per chapter = target length ÷ chapter
count; 350–400 words per page in either theme.

**`source/FACTS.md`**: every number, date and named source the book will use,
rounded on purpose, with the source class next to each; the list of terms
that must be defined on first use; the voice rules. Workers copy from it and
never contradict it. Write it before any chapter, and never let a worker add
a figure that is not in it without reporting the addition.

Post both to chat as the plan, one paragraph each. Do not wait for approval
unless the person asked to see the outline first; they can redirect any time
and a chapter is cheap to rewrite.

## Step 3 — Write chapters with workers

One chapter per worker, `--sandbox fork`, up to eight at a time. Write each
brief to `/workspace/books/<slug>/briefs/NN-slug.md` and give it:

- The book title, the reader, the theme (reading or print), the page budget.
- The chapter's outline block, verbatim.
- The paths: `source/FACTS.md` (read first), `chapters/NN-slug/chapter.md`
  (write here), and the authoring rules below, verbatim.
- "Done" the worker can check: `chapter.md` exists, the frontmatter is
  complete, word count within ±15% of budget, every `##` from the outline is
  present, `python3 /.skills/book-pdf/scripts/build_chapter.py chapters/NN-slug`
  exits 0, and the worker looked at `build/preview/` pages 1 and the last one
  with its read tool and saw no raw LaTeX, no empty diagram boxes, and no
  collapsed lists. Then report: pages, word count, figures, any fact it needed
  that FACTS.md lacked.

Pass `--task <taskId> --todo-index N` so each chapter todo tracks its worker.
When all reports are in, fold the FACTS.md gaps in, fix contradictions
between chapters yourself (units, a number that drifted), and move to the
build. A worker that comes back short is messaged, not replaced.

For a short primer (four chapters or fewer) write it yourself.

## Authoring rules (put these in every brief)

Frontmatter, required:

```yaml
---
title: "How to Think Before You Care"
chapter-num: 1
role: chapter # front | chapter | back
book-title: "The Book Title"
---
```

Structure: one `#` (the chapter title; the theme adds the "CHAPTER N"
kicker), `##` for parts (each starts a new page), `###` sections, `####`
subsections. Open with two or three paragraphs of prose that say what the
chapter settles, then go. No "in this chapter we will".

Prose first. Bullets only for true lists. Define every term on first use with
a definition box. Mechanism, then number, then what it means. Round numbers
and name the source class inline ("IEA, 2025"). Print URLs only in the
further-reading chapter.

Callouts, raw HTML that pandoc passes through:

```html
<div class="callout def">
  <span class="label">Definition</span>
  <p>…</p>
</div>
<div class="callout key">
  <span class="label">Key idea</span>
  <p>…</p>
</div>
<div class="callout example">
  <span class="label">Worked example</span>
  <p>…</p>
</div>
<div class="callout warn">
  <span class="label">Warning</span>
  <p>…</p>
</div>
```

Diagrams, one per 8–12 pages, with a caption; they become numbered figures:

````markdown
```mermaid {caption="Climate is a bathtub. Air pollution is a hose you can turn off."}
flowchart TD
  Tap["Emissions, Gt per year"] --> Tub["Atmospheric CO2 stock, ppm"]
```
````

Keep node labels short and quoted. flowchart, sequence and gantt render well;
avoid pie and mindmap. The renderer rasterizes to PNG, so no `<br>` or HTML
inside labels.

Math: inline `$E = mc^2$`, display `$$…$$` on its own lines. Currency is safe
(`$50T` is not math) but write `USD 50T` in dense financial passages anyway.
Simple formulas read better as Unicode text in a `.formula-block`.

Tables: pipe tables, header row required, at most six columns. They break
across pages with the header repeated; never wrap one in a callout.

Lists: a blank line before every list, or pandoc collapses it into a
paragraph. Lint for `:\n-` before you build.

Print theme only: grayscale reads; anything that depends on color must also
work in black. The reading theme's palette (navy, amber, cream) is
colorblind-safe by design, so meaning is labeled, never carried by hue alone.

## Step 4 — Build, look, fix

```bash
cd /workspace/books/<slug>
bash /.skills/book-pdf/scripts/build_all.sh                  # reading PDF → build/book.pdf
bash /.skills/book-pdf/scripts/build_all.sh --print          # 6×9 B&W → build/book-print.pdf
bash /.skills/book-pdf/scripts/preview.sh build/book.pdf 1 2 3 40 41 <last>
```

Build one chapter at a time while iterating:
`python3 /.skills/book-pdf/scripts/build_chapter.py chapters/03-slug`.
Diagrams are cached by content hash, so a rebuild with unchanged diagrams
takes seconds. A full 180-page book builds in two to three minutes on this
machine; run it in the background and keep working.

Read the preview PNGs with your read tool. Check: the front page has no
"Chapter 0" kicker; chapter openers show the kicker and the rule; running
headers alternate book title and chapter title; math is typeset, not raw
`\frac`; every figure has visible text and a "FIG N.M" caption; lists are
bulleted; no heading sits alone at the bottom of a page; no page is nearly
empty before a table. Fix the markdown, rebuild that chapter, merge again.

Common failures and the fix:

- **Diagram box with no text** → a label used HTML or `<br>`; quote and
  shorten it.
- **Raw LaTeX in the PDF** → a `$` pair crossed a blank line, or a code span
  swallowed it; split the expression.
- **Heading orphaned above a table** → tables may break, headings may not;
  move the heading's paragraph above the table or split the table.
- **Fonts look wrong** → the theme's first choices are Noto Serif and Noto
  Sans, which are on the image; do not add `@font-face` to web fonts, there
  is no network at render time by design.
- **mmdc fails to launch** → Chrome path in `scripts/puppeteer-config.json`;
  `setup.sh` verifies it.

## Step 5 — Deliver

The PDF is a file, not an app: link it in chat and show two preview pages
inline.

```
Done: [<Book Title> (PDF, 177 pages)](sandbox:/workspace/books/<slug>/build/book.pdf)
![Front page](sandbox:/workspace/books/<slug>/build/preview/page-1.png)
![A chapter opener](sandbox:/workspace/books/<slug>/build/preview/page-40.png)
```

If they asked for print too, link `book-print.pdf` on its own line and say
the trim (6×9, B&W, no bleed, ready for Lulu or KDP as an interior). Also
register `outline.md` as a **doc artifact** named "<Book Title> — outline" so
they can request changes chapter by chapter; edits there are the source of
truth for a rewrite.

Mark the task Done with a one-line `detail`: pages, chapters, figures. Then
the accountability lines:

```
Did: 14 chapters by 8 workers, 177 pages, 31 figures, both themes.
Didn't: add a cover — say the word and I'll build a wrap cover from the page count.
Adapted: 3 numbers workers needed were missing from FACTS.md; added and cited.
```

A change request means: edit the chapter (or `FACTS.md` if it is a fact),
rebuild that chapter, merge, re-preview the touched pages, relink.

## Rules

- **FACTS.md is the only source of numbers.** A figure a chapter invents is
  a bug; report it, do not smooth it over.
- **One voice.** The voice block in FACTS.md is law for every worker. You
  read every chapter's first page before the build to catch drift.
- **No filler.** No throat-clearing intros, no bullet walls, no diagram that
  restates the paragraph beside it, no "as of this writing".
- **Look at the pages.** Never deliver a PDF you have not opened in preview.
- Passwords, sign-ins, browsers: none of this needs them. If a source is
  behind a login, ask for the file instead.
