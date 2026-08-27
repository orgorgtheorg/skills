---
name: Skill Tuner
description: Improve or evaluate a learned skill by defining what a good output looks like, scoring a real run against an anchored scale, and applying the smallest edit that closes the gap. Use on "this skill isn't giving me what I want", "is this skill good", "is this ready to share", "make <skill> better", or "tune <skill>".
---

# Skill Tuner

You can't improve a skill you haven't defined "good" for. Every tuning
failure starts the same way: editing toward a vibe. Replace the vibe with a
scale the user built — then refuse to let the scale become a cage.

**What you tune:** skills in your learned list, whose files live at
`/.skills/<id>/`. An edit is a file write — that's how a company forks a
skill to fit itself; note that local edits diverge from the store version
until re-taught. **Never edit the built-in skills.** **The real run:** a
task in this workspace — its transcript, tool calls, and deliverables are
inspectable; "point me at Tuesday's battlecard" beats pasted excerpts. No
real run available → work from the skill alone and flag every place a real
output would have changed the read. **State:** the tuning log at
`/workspace/.gtm-brain/tuning/<skill>.md`, one line per experiment, restated
after every re-score.

## The flow — four moves

### 1. What does good look like?

Ask the user to define a good output in their words — one short chat
question, or a 3-question form if they're stuck (last output that felt
right and why; the moment one went wrong — that moment is usually the
definition, inverted; who consumes it and what they do in the first thirty
seconds). If they can't articulate it or want one-shot: draft the
definition yourself from the skill's purpose and the run, **label it as
your proposal**, proceed. A definition they can argue with beats a stalled
session.

### 2. Build the calibration scale — together

**About three criteria, each 1–10, each anchored.** Three forces naming
what matters; ten is a rubric pretending to be a standard, and rubrics get
gamed. Each criterion comes from _their_ definition ("call-ready without
edits", not "clarity"). Anchor the numbers in terms of this skill's actual
outputs — what a 3, a 7, a 10 look like — or they're decoration. **The
scale describes the output, never the procedure.** Propose the draft; they
push back; settle in a round. Scale changes later get a version bump so
old scores aren't misread.

### 3. Assess — scores, evidence, three ways to a 10

Score the run in the tuning doc: each criterion n/10 with **the sentence in
the output (or the absence) that earned it** — a score without a pointer is
an opinion wearing a number. One honest overall line.

Then, non-negotiable: **three distinct paths to a 10, delivered as one lead
and two ranked alternates — never three assignments.** Typically they
differ in kind: an edit to the skill's instructions, a piece of context to
feed it, a change to the output's shape. Every one concrete enough to apply
in under a minute: when the fix is an instruction edit, give the exact line
to remove and the exact line to put in its place — "tighten the summary" is
a suggestion you're not allowed to make. Predict what should visibly differ
in the next run and which criterion moves.

Offer to apply the lead edit yourself (it's a file write). **One change per
re-run** — stack three and you'll never know which worked, and you'll be
afraid to remove any of them forever. Chat: two lines — the scores and the
lead change.

### 4. Re-score and keep the log

After a change lands and the same input re-runs, re-score on the same
scale. Log: what changed → which score moved → KEEP or REVERT. Score didn't
move → revert it; you've learned where the problem actually lives. Never
re-suggest a reverted change. And question the scale too: a run that scores
high but feels wrong is missing a criterion — fix the scale, not the skill;
a middling score that delighted its audience means a criterion is
over-weighted. Show score history as a small chart in the tuning doc when
there are 3+ rounds.

## Guideposts — a standard, not a cage

- **No tight-little-box evals.** If the scale starts specifying structure,
  phrasing, or step order, push back — a skill optimized to a rigid rubric
  loses to the bare model within a release; every procedural rule freezes
  the skill at yesterday's model.
- **Non-negotiable behaviors are contracts, not criteria** — "never
  fabricates a number" is pass/fail, separate from the 1–10s, earned by
  repeated failures rather than brainstormed.
- **When the improvement isn't obvious, say so** — best read labeled as a
  judgment call, or the one question that resolves it. Never manufacture a
  confident rule to fill silence; invented fixes are how skills accrete
  scar tissue.
- **Don't add a rule the model already follows.** Test: would the output
  have been wrong without it? On every model upgrade, re-test and delete
  rules the base model now follows — sometimes the tune is subtraction.
- **One bad run is an anecdote.** Codify on the second occurrence.

## Readiness — the same scale, harder questions

"Ready to share?" adds: does it beat the bare model on the same input (if
it only ties, it's dead weight)? Can a stranger get value cold — what does
it silently assume the builder knows? Does the description alone trigger
correct use? A skill only its builder can drive is a personal prompt
wearing a skill's clothes — a fine thing to be; name it, don't ship it as
more.

## What NOT to do

- Don't assess without a stated (or explicitly proposed) definition of good.
- Don't exceed ~three criteria or let them describe procedure.
- Don't make more than one change per re-run, or deliver three co-equal
  assignments.
- Don't give a suggestion the user must translate before applying.
- Don't re-suggest what the log shows was reverted.
- Don't touch built-in skills, and don't tune a companion skill you haven't
  actually read from disk.
