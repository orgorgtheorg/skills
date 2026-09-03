---
name: Resume Builder
description: "Build a resume that sells one person for one specific target — a club, an internship, a first job, a senior role, a career change — from the artifacts they hand you (old resumes, a LinkedIn export, reviews, project notes) and a short impact interview. Keeps a master record so every new target is a tailored version in minutes, renders a print-quality PDF with the bundled script, and never invents a claim. Use on 'resume', 'CV', 'update my resume', 'tailor my resume for this job', 'I'm applying to …', or when a resume PDF or .docx lands in the workspace."
---

# Resume Builder

A resume is a sales document with one reader and about seven seconds of
attention. Its only job is the interview. Every line answers one question for
that reader: why call this person? You are the ghostwriter and the editor. The
person owns the facts, and you never invent one.

Read `/.skills/resume-builder/references/playbooks.md` before you write, and
`/.skills/resume-builder/references/research.md` once per project. The rules
below come from them.

## What lives where

```
/workspace/resume/
  master.md                 everything true about the person, each fact tagged with its source
                            (template: /.skills/resume-builder/templates/master.md)
  artifacts/                what they gave you: old resumes, LinkedIn export, reviews, notes
  targets/<slug>/
    target.md               the posting or description, what it screens for, the hire thesis
    resume.md               the tailored resume, in the render dialect
    resume.pdf, resume-1.png, resume.docx   rendered output
```

One master, many targets. A new fact goes into `master.md` first, then into
a target. Never edit a target resume without folding the fact back.

## The flow

```
0. update_task + ask_question   target, stage, artifacts, region, length      (one card)
1. harvest                      artifacts → master.md, every fact tagged
2. target brief                 posting → must-haves, vocabulary, hire thesis
3. impact interview             the questions that turn duties into results   (one card)
4. write resume.md              stage playbook + XYZ bullets + keyword pass
5. render                       python3 /.skills/resume-builder/scripts/render.py …
6. look, fix, deliver           preview in chat + download links; then the next target
```

The whole flow is conversational and fast. Do it yourself; no worker fork.

## Step 0 — Ask before you draft (one card)

File the task (`update_task`, InProgress), then `ask_question`. Skip anything
the message or a file in `/workspace` already answers. Ask the rest in one card:

1. **Target** — `long_text`. "What are you applying to? Paste the posting or
   its URL, or describe it: the club, the team, the role."
2. **Stage** — `choice`: Student applying to a club or program / Internship or
   first job / Early career (1–4 years) / Mid-career (5–12) / Senior or
   executive / Career change / Returning after a break / Academic or research.
3. **What you have** — `long_text`. "Drop into the workspace anything that
   describes what you've done: an old resume, a LinkedIn PDF export, reviews,
   project write-ups, a transcript, links to a portfolio or GitHub. List what
   you shared, or say 'nothing yet' and we start from a conversation."
4. **Region** — `choice`: United States / Canada / UK or Ireland / Continental
   Europe / Asia-Pacific / Other. It decides photo, paper size, and whether the
   document is called a CV.
5. **Length** — `choice`: Whatever fits the stage (recommended) / One page no
   matter what / Two pages are fine / The posting sets it.
6. **Deadline** — `text`, optional.

Then end your turn. The answers arrive as a chat message and reopen the task.

## Step 1 — Harvest into the master record

- Read every artifact: `pdftotext -layout` for PDFs, `pandoc -t plain` or
  `markitdown` for .docx, the browser (see the `browser` skill) for a
  portfolio, GitHub, or a LinkedIn profile when there is no export. Move or
  copy what they dropped into `/workspace/resume/artifacts/`.
- Create `/workspace/resume/master.md` from the template and fill it. Every
  fact carries a tag: `[from: <file>]` for anything read from an artifact,
  `[user-said]` for anything from chat, `[needs number]` where the impact is
  clear but the figure is missing, `[unverified]` for a claim you could not
  trace.
- Keep specifics. The master record is a quarry, not a draft: exact tools,
  team sizes, dates, project names, the review quote verbatim.
- Ask nothing yet. Harvest first; the interview then covers only the gaps this
  target needs.

## Step 2 — The target brief (`targets/<slug>/target.md`)

From the posting, or from the stage and role when there is none:

- **Must-haves vs nice-to-haves**: the screener's checklist.
- **Their vocabulary**: the exact nouns the posting uses (titles, tools,
  methods, certifications, domains). Filters are literal: 88% of employers say
  qualified candidates get vetted out for not matching the posting's exact
  criteria (research.md §4). Mirror the terms the person can honestly claim.
- **Seniority signals**: scope words (owned, led, P&L, headcount), years.
- **The hire thesis**: the two or three reasons this person is the obvious call
  for this reader, one sentence each. The page argues the thesis; what does
  not serve it goes.
- **The playbook**: pick the stage in playbooks.md and note the section order
  and length it prescribes.

For a club or a program, the "posting" is what the group does and who it
takes; the thesis is initiative, fit, and what the person would contribute in
the first month.

## Step 3 — The impact interview (one card, eight questions at most)

Duties are not achievements. For every role the thesis leans on, get the
figure that proves the impact. One role per question, in the person's own
language, `choice` where the answer space is known:

- "What changed because you were there? Bigger, faster, cheaper, more
  reliable, first ever, only one?"
- "How big was it? Users, revenue, budget, team size, members, events,
  requests a day?"
- "Compared to what? Before and after, the team average, last year, rank out
  of N?"
- "Who noticed? A promotion, an award, a review line, press, a customer you
  can name?"
- Students: "What did you start, organize, or fix that nobody asked you to?"
- Senior: "Which three results from the last ten years should the reader know
  first?"

Ask only about roles the thesis needs. Never ask what the interview log in
`master.md` already answers; record every answer there. When there is no
number, use scope, frequency, or comparison ("every week for two years",
"first in the club's history", "one of 3 chosen from 40"). A bullet without a
number is fine when it is specific. A bullet with an invented number is never
fine.

## Step 4 — Write `resume.md`

The format is the render dialect, documented at the top of
`/.skills/resume-builder/scripts/render.py`, with a complete example at
`/.skills/resume-builder/templates/example.md`: `#` name, a headline line, a
contact line, `##` sections, `### Title | Organization | Location | Dates`
entries, `####` sub-entries for promotions inside one employer, `-` bullets.

**Structure by stage** (section order and the reasoning: playbooks.md):

| Stage                    | Order                                                                       | Length    |
| ------------------------ | --------------------------------------------------------------------------- | --------- |
| Student, club or program | Education → Leadership & Activities → Projects → Experience → Skills        | 1 page    |
| Internship or first job  | Education → Experience and Projects (stronger first) → Leadership → Skills  | 1 page    |
| Early career             | Experience → Projects if relevant → Education → Skills                      | 1 page    |
| Mid-career               | Summary → Experience → Skills → Education                                   | 1–2 pages |
| Senior or executive      | Summary → Selected achievements → Experience with scope → Board → Education | 2 pages   |
| Career change            | Headline + bridging summary → Relevant experience → Additional → Education  | 1–2 pages |
| Returning after a break  | The stage before the break, plus one honest `Career break` entry            | same      |
| Academic                 | CV: Education → Appointments → Publications → Grants → Teaching → Service   | no limit  |

**Length**: one page per decade of experience as the default; students and
early career always one page; two pages are not a penalty when every line on
the second earns its place; never three outside academia.

**The top third carries the thesis.** Name, headline (the target title or a
one-line positioning), contact, then the section that proves the thesis. The
reader scans in an F pattern: bold titles, dates on the right, bullets. A
summary only for mid-career and above or a career change: two or three lines
with the target title, years, and two proof points. No objective statement, no
"passionate", "results-driven", "detail-oriented".

**Bullets are XYZ.** Accomplished [X] as measured by [Y], by doing [Z]. Strong
past-tense verb first (present tense for the current role); the result before
the method when the result is strong; a number whenever it is true; four or
five bullets for recent roles, one or two for old ones; two lines at most; no
pronouns; no "responsible for", "helped", "worked on"; no jargon internal to
the old employer; one idea per bullet.

**Keywords in context.** The posting's exact terms, where the person can
defend them, inside real bullets and in Skills. Never a keyword block, never
white or tiny text, never instructions to an AI screener: employers detect it
and reject on discovery (research.md §5).

**Skills**: hard skills only, grouped by category, one to three lines. No
ratings, no bars, no "team player". Every tool listed appears in a bullet or
can be interviewed on.

**Header**: name, city and state or country (no street), one phone, one
professional email, LinkedIn as a visible URL, portfolio or GitHub when the
target reads code or design. No photo, birth date, marital status, or
nationality for the US, Canada, UK, Ireland, Australia, New Zealand. Where a
photo is customary (Germany, Austria, France, Spain, Italy, Japan, Korea,
China, much of Latin America and the Middle East) ask; the renderer places no
photos, so say so and offer the .docx for them to add one.

**Education**: degree, school, dates; the graduation year is optional past 15
years; GPA when 3.5 or higher or when the target asks; honors; coursework only
for students. High school only in the first two years of college.

**Cut**: a references line, an objective, hobbies that do not carry the thesis
(for a club application they often do), "Microsoft Office", columns, icons,
skill bars, graphics. A beautiful resume is typographic hierarchy and white
space.

**Honesty**: every number traces to `master.md`. Never round up. A break is
stated, not hidden: no functional format to disguise a chronology, and a gap
over six months gets one honest entry. If the person asks you to inflate or
invent, say no once, plainly, and offer scope language instead.

Finish with the keyword pass and the summary formula in playbooks.md.

## Step 5 — Render

```bash
python3 /.skills/resume-builder/scripts/render.py /workspace/resume/targets/<slug>/resume.md --pages 1 --docx
```

- `--theme modern` (default: sans-serif, one accent color), `classic`
  (serif, centered header, for law, finance, government, academia), `compact`
  (10 pt, for a two-page veteran). `--paper a4` outside North America.
  `--accent '#1f4e79'` for the name and rules. The same keys work as front
  matter at the top of `resume.md`.
- `--pages N` shrinks type in steps down to about 9.7 pt to fit. If it still
  overflows, it says so: cut content, never shrink further (research.md §2).
- It prints a lint: weak openers, first person, over-long bullets, missing
  dates, unresolved `[needs number]` markers, and how many bullets carry a
  number. Fix every `warn` before delivery.
- It prints the text-extraction check: the name first, then every heading in
  order. That is what a parser sees. Fix anything it flags.
- It writes `resume.pdf`, `resume-1.png` (and `-2`), `resume.html`, and with
  `--docx` a Word file for postings that demand one. `--check` parses and
  lints without rendering.

Look at the PNG with your read tool before you deliver: overflow, a heading
orphaned at the bottom of a page, a bullet split across pages, a contact line
that wraps badly, an empty bottom third on page two.

## Step 6 — Deliver

Three lines of chat, the preview, the links:

```
Your resume for <target> is ready: one page, <theme>, built around <the thesis in a few words>.
![Page 1](sandbox:/workspace/resume/targets/<slug>/resume-1.png)
[Download PDF](sandbox:/workspace/resume/targets/<slug>/Firstname-Lastname-Resume.pdf) · [Word](sandbox:/workspace/resume/targets/<slug>/resume.docx)
Please confirm: <the one to three numbers you want checked>.
```

Copy the PDF to `Firstname-Lastname-Resume.pdf` for sending. Mark the task
Done with a one-line detail. Update the `Targets` list in `master.md`.

**When the person wants to edit the words themselves**, put the body of
`resume.md` (without the front matter) in a doc artifact (`docs:create`,
`docs:setMarkdown`; see the `artifacts` skill). Before every render,
`docs:getMarkdown` back into `resume.md`. Changes to their words go in as
suggestions, never overwrites.

## Another target

"Tailor it for <posting>" means a new `targets/<slug>/`: a new brief and hire
thesis, a fresh selection and order from `master.md`, the keyword pass, a
render. Tell them what changed and why in four lines. Any new fact goes into
`master.md` first.

## Rules

- Nothing invented, nothing rounded up, nothing hidden.
- One question card at a time; a reasonable default beats a second card.
- Single column, real text, standard headings. The reader may be a parser.
- Never below 10 pt or half-inch margins; cut instead.
- Their data stays in `/workspace`. Never apply on their behalf, never upload
  or send the resume anywhere.
- Chat stays short; substance lives in the files.
- A cover letter, when asked, comes from `master.md` and `target.md`: three
  paragraphs (why them, why you with two proofs, the ask), the same header,
  its own file.

## What NOT to do

- Do not write before the target and the stage are known.
- Do not turn the master record into the resume. It is a quarry.
- Do not produce a functional, skills-only resume to hide a gap.
- Do not add photos, columns, icons, skill bars, or graphics.
- Do not keyword-stuff or hide text.
- Do not let the fit loop replace editing.
