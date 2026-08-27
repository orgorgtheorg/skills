---
name: Living Competitive Intel
description: Keep an always-current, source-weighted brief per competitor, refreshed on a schedule and presented as a diff against the last run. Use on "what's new with <competitor>", "track <competitor>", "refresh competitive intel", "did they change pricing", "prep me on <competitor> before a call", or a segment question like "how do they play in mid-market healthcare".
---

# Living Competitive Intel

Intel is only useful if it's current and weighted. Your job: research each
tracked competitor with your browser, weight every finding **by what kind of
claim it is**, and surface the **diff** — what moved since the last brief —
not a re-dump of what's already known. A competitor's marketing tells you how
they _position_, never what's _true_.

State lives at `/workspace/.gtm-brain/intel/<competitor>/brief.md` — a doc
artifact updated in place. The prior brief is a real file, so the diff is
computed, never remembered. If `/workspace/.gtm-brain/company-context.md`
exists, read it for "what do we sell" and the segments that matter; otherwise
ask the two intake questions below.

## First run

If the competitor isn't named, ask for it in one chat line and stop — no
methodology tour, no sample brief. If the brain file doesn't say what the
company sells, ask that too (same message, two lines total). Then run — no
other setup. Offer once to create a **weekly schedule** per tracked
competitor; the brief also refreshes on demand.

## The sweep — one task, todos ticking

1. **Scan.** Browser: their site, pricing page, changelog, careers page,
   third-party reviews (G2, Trustpilot), community chatter, news. Long crawls
   go to background commands — let them wake you. Fold in any internal deal
   signal the user dropped in `/workspace/`.
2. **Weight.** Score every finding by claim type (see Source weighting). A
   capability claim from their marketing is a _lead to verify_, not a fact.
3. **Diff.** What's new, moved, or disappeared since the last brief — each
   dated, with the so-what. First run: say "as of today", no invented delta.
4. **Verify-these.** The 3–5 load-bearing or negative claims a human should
   confirm against a primary source. Raise as one **non-blocking your-move
   Ask** — you keep working; the human confirms when they can.

Chat gets two lines: "Brief's refreshed — the diff leads. One thing moved
that should change how you sell against them: <one clause>." Everything else
is in the doc.

## The brief (doc shape — lead with what moved)

```
WHAT MOVED       change · source+date · so what
POSITIONING      how they frame themselves now (their words = positioning, not truth)
PRODUCT/PRICING  verified facts, dated; capability claims marked [verify]
MARKET SIGNAL    reviews/community/news in aggregate
LENSES           segment quick hits, only where signal supports a cut
DEAL TERMS       where we win · where we honestly concede · eval conditions favoring them
VERIFY THESE     short, load-bearing
```

## Lens views — the same truth, cut by segment

A segment question gets a segment answer — the lens alone, never lens plus
full brief bolted on. Cuts: INDUSTRY · GEO · SIZE. Lens discipline:

- Each row is a quick hit: one DO, one WHY with a date, two or three lines
  max. Action-first — "push the eval to X", "don't concede Y here" — never a
  recap of their story.
- Rows inherit the full source weighting and honesty tiers; an unanchored DO
  carries `[pattern-matched]` or `[unverified]` inline.
- **Insufficient signal is a valid row**: `insufficient signal — <what would
unlock it>`. Never stretch a global read into a fake segment read.
- No delta from the main brief → `no segment-specific delta`, one line.

**Pre-call fast path.** "I'm about to talk to a bank — what do I need on X"
gets **chat only, five lines max**: the one DO, the one landmine to expect,
one `[verify]` item. No doc update, no other rows. The trimming never trims
the check — those five lines pass the same bar as a full brief. Footer: say
"full brief" for the rest.

## Source weighting (the real IP)

- **Perception claims** ("their onboarding feels slow") → customer/prospect
  voice and aggregate community signal beat the web.
- **Hard facts** ("no SSO on the base tier") → primary source wins (their
  docs/pricing/changelog); a single claim is a lead to verify.
- Order of trust: first-party deal evidence → primary competitor sources →
  independent third party → competitor marketing → model inference
  (`[unverified]`).
- **Recency wins** — fresh signal expires stale. **Negative claims carry the
  highest bar** — they may have shipped it last month.
- **A positioning change is itself the highest-value signal.** Read it
  forward (where they're steering, which buyer they now chase), never
  backward as fact about their product.
- Honesty tiers everywhere: **anchored** / **pattern-matched** / **reasoning**.
  Never collapse a guess into a fact.

Before the brief ships: steelman the competitor's move (strongest read of why
they did it), run each so-what through **Ownable / Defensible / Distinctive /
Sourced**, confirm DEAL TERMS is honest about where you concede, and name the
one shift that should change how the team sells — not just this week's news.

## What NOT to do

- Don't treat competitor marketing as truth about their product.
- Don't bury the diff under a re-dump; don't manufacture a change to look
  useful — "nothing material moved" is a valid, valuable answer, and the
  task ends _ended_ (routine), not _done_.
- Don't over-index one community thread or one lost deal — weight the
  aggregate.
- Don't fill a lens for symmetry; an honest empty row beats a confident
  fabrication.
- Don't put the brief in chat. Two lines and the pointer.
