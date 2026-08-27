---
name: Voice of Customer
description: Maintain a living weekly voice-of-customer digest built on verbatim, attributed quotes from call transcripts in the workspace — what customers said, what shifted (counted), account arcs across weeks. Use on "VOC digest", "what are customers saying", "digest these transcripts", "weekly customer voice", or when transcripts land in /workspace/transcripts/.
---

# Voice of Customer

Extraction plus continuity. Customers said specific things in specific words —
those words are the asset, and you keep them raw. What no single week's
digest can contain is the _shift_: what's said more, less, or differently
than before, which account is on week four of an arc, which objection just
got called "new" for the second time. The quotes are the asset; the memory is
the edge.

**Inputs:** transcripts in `/workspace/transcripts/` (uploaded, pasted into
chat and saved there, or dropped as files). **State:** the digest doc at
`/workspace/.gtm-brain/voc/digest.md` (a doc artifact updating over itself)
and the quote registry at `/workspace/.gtm-brain/voc/registry.json` — every
quote ever used, with full attribution.

## The quote contract (the hardest rules)

- **Verbatim, real, traceable.** From a transcript you were given, trimmed
  for length only, never paraphrased, never improved. One invented or
  mis-joined quote makes the whole digest worthless.
- **Full attribution, every time:** account · speaker role · date · source
  call · timestamp where available. The account name stated explicitly.
- **Speaker check.** A quote in a customer-evidence slot is from a
  _customer_. A rep's framing is pitch, not voice of customer — label it.
- **The registry check.** Before reusing or newly attributing a quote, check
  the registry: the same sentence at the same timestamp cannot belong to two
  accounts. Conflict → flag it, never pick a winner.
- **Transcription cleanup, narrow.** Fix speech-to-text garble only when the
  correction is unambiguous, marked. Never guess a quote into fluency.

## The digest (one living doc)

```
VOC DIGEST · updated <date> · window <first week> → <this week> · calls this week: <n of N known>

WHAT MOVED THIS WEEK   the shifts, counted — lead here
THE THEMES             theme named in THEIR words → quotes, attributed in full
ACCOUNT ARCS           <account> · dated beats · what changed this week
WORTH ESCALATING       insight → action → who should see it
WATCHING               directional signals not yet trends — named as such
GONE QUIET             what stopped being said, and since when
CHANGELOG              date · what shifted · why it matters   (append-only)
```

- Theme names use the customers' vocabulary ("we can't tell who touched the
  data"), never yours ("visibility gaps"). If a customer handed you the
  headline, use it. More quotes beats fewer.
- **A trend word requires a number.** "Intensifying", "consistently",
  "continues to" — banned unless a count sits beside them or the claim is
  labeled _directional_ with the reason. State coverage: how many calls this
  week, and whether that's all of them.
- **Account arcs:** an account's second appearance starts an arc. The
  four-week deal arc and the three-week deterioration are the highest-value
  stories a snapshot can't see.
- Before calling anything "new", check the history — "third week running" is
  more useful anyway.
- **Gone quiet is a finding.** A dominant objection that vanishes is worth
  naming.
- **No quotas.** Sections hold what the week produced — three escalations
  one week, zero the next. Empty sections say "nothing this week" and earn
  trust by it.

## Cadence and escalation

Offer once to create a **weekly schedule**. First run with no history is the
**baseline week** — count nothing as a trend; one week has no direction.
Each scheduled run: fold the new week in, refresh counts, advance arcs,
retire what went quiet (noted, never silently deleted), append the
changelog. Chat gets one or two lines: "VOC's updated — competitor mentions
2 → 7 over six weeks; that one's worth a look."

**Worth escalating** entries cross team lines by design: @-mention the
teammate who should see it, or raise a non-blocking your-move Ask on the
owner. Quietly filing sales-critical signal under "marketing" wastes the
point.

**The dashboard.** When the quote base outgrows a document (roughly 50+
quotes or the user wants to explore rather than read), offer a **custom-app
artifact**: sortable, filterable by competitor · account · segment · theme,
built on the registry. The digest doc stays canonical — the app renders the
same store, never becomes a second source of truth.

Hand-offs: counted competitor mentions and the verbatim lines around them
feed Living Competitive Intel; recurring objections feed the Skeptic. Check
the learned-skills list before offering; if absent, deliver the attributed
material anyway and note in one line what teaching it would add.

## What NOT to do

- Don't summarize quotes into corporate language — "customers expressed
  concerns regarding data governance" is the failure this skill exists to
  prevent.
- Don't use a trend word without a count or a "directional" label.
- Don't declare a trend from one week or one loud customer.
- Don't start a new document each week — update the living one.
- Don't fill sections to a quota or trim to a template.
- Don't let a rep's words land in a customer slot.
- Don't paste the digest into chat — one or two pointer lines.
