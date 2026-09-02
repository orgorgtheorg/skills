---
name: LaTeX Math Rendering
description: "Render math properly in a custom app you build: add KaTeX, drop in the bundled <Math> and <MathText> components, and — most importantly — capture the math AS LaTeX, transcribed from the source, instead of the garbled symbols that plain text extraction produces. Use whenever the user's material contains formulas, equations, integrals, matrices, or chemistry, or whenever an app shows math as raw backslash text or mangled characters."
---

# LaTeX Math Rendering

Custom apps (see the `custom-app` skill) ship with no math renderer. Any formula
you put on screen shows as literal text such as `\int_0^1 x^2 dx` — or worse, as
the mangled characters that plain text extraction produces (`√10` comes out as
`s10`, `∫₀¹` becomes `y 0 1`, fractions collapse into a jumble). This skill fixes
both halves of the problem: rendering the math, and capturing it correctly in
the first place.

## When this applies

- The user's source has math: a textbook, problem set, lecture notes, a
  formula-heavy spreadsheet, a chemistry, physics, or statistics reference.
- An app you built, or are building, shows equations as raw LaTeX, backslashes,
  or garbled symbols.
- The user says "render the equations", "the math looks wrong", "symbols are
  broken", or asks for "proper formulas".

Read this whole file before you touch the app.

## 1. Add KaTeX to the app (once per app)

```bash
cd /workspace/app && npm install katex @types/katex
```

The first install replaces the symlink to the shared node_modules cache with a
real folder. That is expected; do not "fix" it.

## 2. Copy in the bundled component

```bash
cp /.skills/latex/scripts/math.tsx /workspace/app/src/components/ui/math.tsx
```

It exports two components and depends only on `katex`:

- `<Math>` renders ONE LaTeX expression, inline by default, or as a centered
  block with the `display` prop.
- `<MathText>` renders a paragraph that CONTAINS inline math. Plain text stays
  text; spans wrapped in `$…$`, `$$…$$`, `\(…\)`, or `\[…\]` become rendered
  math. Use it for problem statements and explanations.

Invalid LaTeX renders in place (KaTeX runs with `throwOnError: false`), so a
rough transcription never crashes the app.

## 3. Load the stylesheet once

In `/workspace/app/src/main.tsx`, next to the existing `./globals.css` import:

```ts
import "katex/dist/katex.min.css";
```

Without it the math renders as unstyled, misaligned text. Vite bundles the CSS
and its fonts, so the app stays offline-safe and no CDN is involved.

## 4. Render

```tsx
import { Math, MathText } from "./components/ui/math";

// One expression, inline:
<Math>{"\\int_0^1 x^2\\,dx"}</Math>

// One expression as a centered block:
<Math display>{"\\frac{dy}{dx} = 2x"}</Math>

// Prose with inline math (a problem statement):
<MathText>{"Evaluate $\\int_0^1 x^2\\,dx$ and simplify."}</MathText>
```

Inside a JSX string literal every LaTeX backslash must be doubled (`\\int`).
When the LaTeX comes from Convex data it is a plain string, so pass it through
as-is: `<Math>{problem.latex}</Math>`.

## 5. Capture the math AS LaTeX — the rule that matters most

Rendering only works when the stored text is LaTeX. Plain text extraction
destroys math, and no renderer can recover it.

- Never paste `pdftotext` output, or any plain-text extraction, that contains
  math into the app or the database. It cannot be rendered.
- If your model accepts images: render the page to an image (for example
  `pdftoppm -png -r 150 -f 12 -l 12 book.pdf page`, or a Python PDF library)
  and transcribe each formula to LaTeX from the picture.
- Otherwise: reconstruct the LaTeX from the garbled text plus the surrounding
  context — you know whether it is calculus, linear algebra, or chemistry — and
  flag anything you are unsure about so the user can check it.
- Store the LaTeX string in Convex (for example a `latex` field on each
  problem), never the raw extraction. Render it with `<Math>` / `<MathText>`.

## Rules

- Use KaTeX bundled through Vite. Do not reach for MathJax, a CDN `<script>`
  tag, or an iframe; they are slower, need the network, and fight the starter's
  build.
- `<Math>` inherits `currentColor`, so it follows the workspace's light/dark
  theme automatically. Do not hardcode colors around it.
- Install KaTeX once per app. Do not reinstall on every edit.
- Keep the component file where the starter keeps its primitives
  (`src/components/ui/`), so it matches the app's conventions.
