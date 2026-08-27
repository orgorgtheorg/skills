---
name: GTM Brain Builder
description: Build or refresh the company's GTM brain — /workspace/.gtm-brain/company-context.md, the context file other GTM skills read. Use when the user asks to onboard the company, set up or refresh GTM context, or complains that marketing output sounds generic. Also run it automatically whenever another GTM skill needs company context and the brain file is missing or thin — never let a downstream skill fail on missing context.
---

# GTM Brain Builder

You are building `/workspace/.gtm-brain/company-context.md` — the file that
makes every other GTM deliverable sound like this company instead of like an
AI. The core idea: **reacting is faster than generating.** Draft the whole
file from almost nothing, mark what's missing, and let the operator correct a
strawman instead of writing from blank.

Incompleteness is a valid end state. A brain with four good fields and twelve
marked gaps is useful today.

## The run — file it as one task

File a task with these todos and check them off as you go: research sources /
opener form / draft the brain / confirm against draft / review gate / handoff.

### 1. Research from the URL

Ask for the homepage URL in chat (one line) if you don't have it. Then use
your browser: homepage, /about, /pricing, /customers or case studies, the two
most recent blog posts. Once competitors are named, their homepages too.

Run the AI-strip filter on scraped copy: "the AI-powered platform for modern
teams" does not get transcribed as fact and does not get a invented
replacement — mark it `[WEAK: homepage claim doesn't survive AI-strip]`.

### 2. The five-question opener — a form artifact

Create a form artifact (see the `forms` skill) with exactly these, intro copy
"First guesses are fine — a wrong guess I can fix is worth more than a blank
I can't":

1. Elevator pitch — even a draft
2. ICP — even a guess
3. 1–2 companies you're most likely compared to
4. Your most important differentiator
5. Any brand attribute that should shape how everything sounds (skippable)

Keep working while answers stream in. Anything flagged as a guess gets tagged
`[operator-guess]`. If they answer nothing, proceed — the research alone
produces a draft.

### 3. Draft everything in one pass — a doc artifact

Create the brain as a **doc artifact** backed by the file, all six sections,
no stopping to ask. Three markers, and only three:

| Marker              | Means                          |
| ------------------- | ------------------------------ |
| `[MISSING: <what>]` | Nothing in any source          |
| `[WEAK: <why>]`     | Present but fails a filter     |
| `[operator-guess]`  | Operator flagged it as a guess |

**Never invent.** A confident fabrication is worse than a marked gap, because
the gap gets fixed and the fabrication gets repeated in a sales deck. Keep
subsection headings even when content is missing.

The six sections: **Positioning** (elevator pitch · competitive alternatives ·
unique attributes, AI-strip required · value · category), **Customer** (ICP ·
verbatim customer language · coverage line), **Operational** (top competitors
by deal frequency · product snapshot · tool stack), **Voice + POV** (3–5
adjectives · brand attribute · love/never-use phrases · the contrarian
belief), **Proof** (one line each), **Ownership** (owner · audit log ·
contradiction log). Frontmatter carries `status`, `last-updated`,
`customer-evidence-last-added`.

### 4. Confirm against the draft — a second form

Hard cap: **seven questions**, each a confirmation, never open-ended.
"I drafted _Head of Security at 200–2000-person SaaS_ from your customers
page" with choices **Right / Close / Wrong** plus a text field — never
"What's your ICP?". Rank by blast radius (how many downstream skills degrade
without it): customer language, ICP, unique attributes, competitors,
elevator pitch, POV, tool stack. Where discrete candidates surfaced, offer
them as picks.

### 5. One review gate — a decision Ask

One blocking decision Ask: "Brain's drafted — anything wrong before I mark it
live? I'll fix what you flag and leave the rest marked." One gate, not six.
Then set `status: live`.

### 6. Handoff — two chat lines plus one your-move Ask

Green light the moment four fields exist: elevator pitch, ICP, top 2–3
competitors, one differentiator that survives AI-strip. Say so plainly.
Report gaps ranked by blast radius, not count. Then the one upload that
matters, as a **non-blocking your-move Ask**: "Drop one customer call
transcript or three customer emails into /workspace/transcripts/ — I'll pull
verbatim quotes only." Customer language is the only section that can't be
reconstructed from public material.

Offer once (never nag) to create a monthly schedule that checks
`customer-evidence-last-added` and asks for fresh evidence when it passes
30 days.

## Provenance and evidence weighting

Tags survive into the file: `[from: homepage]`, `[from: transcript-<date>]`,
`[operator-guess]`. Never tag anything "operator-confirmed" — a stale
confirmation is a trap; an open guess is honest. When sources disagree,
weight by proximity to a real customer: direct customer contact 3x, operator
assertion 2x, the company's own marketing 1x. When 1x contradicts 3x, flag
it in chat — never silently pick a winner. That gap is the most valuable
thing this skill produces.

When new evidence contradicts the brain, pose a decision Ask — **Evolve**
(the market moved, the brain follows) / **Hold** (one account, not a trend)
— with your read labeled as a lean. Record the verdict in the contradiction
log. Never overwrite silently; an unanswered Ask is logged `open` and
re-asked, because staying put by silence isn't a decision.

## For other GTM skills (the contract)

Any skill needing company context: read
`/workspace/.gtm-brain/company-context.md` first. Missing → run this skill
instead of failing. Respect the markers — `[MISSING:]` stays a placeholder,
`[operator-guess]` is provisional. Weight `[from: homepage]` below
operator-supplied. If `customer-evidence-last-added` is older than 30 days,
say so in one chat line, then proceed. Never block on staleness.

## Hard rules

1. Never require a document. URL plus five guesses is the floor.
2. Draft before you interview. Always.
3. Never invent — mark it or ask.
4. Seven confirmation questions maximum; usable file at every checkpoint.
5. One review gate, not one per section.
6. Verbatim customer language: quote marks or it doesn't count.
7. AI-strip filter on every differentiation claim.
8. Chat stays to one or two lines; substance lives in the doc and the forms.
