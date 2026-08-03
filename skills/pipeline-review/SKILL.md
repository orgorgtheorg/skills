---
name: Pipeline Review
description: Review a sales pipeline export and cross-check the user's LinkedIn network for warm intros. Use whenever a pipeline/CRM export (CSV/Excel) lands in the channel or the user asks to review a company's pipeline or find paths into accounts.
---

# Pipeline review & warm intros

The user is a sales expert advising a company's sales team (often a portfolio
company). Two jobs, in order: (1) a fast, opinionated read of their pipeline
so the user can give good feedback on the call, (2) the accounts where the
user's own network opens doors. Job 2 is usually the most valuable thing they
bring — never skip it when the LinkedIn export is available.

## Inputs

- **Pipeline export** (required): CSV/Excel under `/workspace/uploads/` or
  dropped in the channel. Column names vary by CRM — map by meaning, not
  exact header: account, stage, deal value, owner, close date, last activity,
  next step, champion. If a critical column is missing, say what's missing
  and do the best read possible rather than refusing.
- **LinkedIn export** (for step 2): `Connections.csv` from the user's
  LinkedIn data-export zip (note: it starts with a "Notes:" preamble line
  before the real header). `messages.csv`, when present, shows who they've
  actually talked to — weight those connections higher.
- **Meeting notes** (optional): anything under `/workspace/uploads/granola/`
  about this company — use for context the CRM can't show.

If only one input is present, do what it enables and ask for the other.

## Step 1 — Pipeline overview

- **Shape**: total $, count/$ by stage, average deal size, and top-3
  concentration (above ~50% is itself a finding).
- **Health flags**, each naming the specific accounts: no next step, stale
  > 21 days, slipped close dates, big deals stuck in early stages,
  > single-threaded (one champion, no exec contact).
- Then 3–5 blunt observations a sales veteran would make — name accounts,
  no hedging.

Deliver as a **sheet** (the numbers) plus a **short doc** (the read). One
screen; the user should absorb it in two minutes before their call.

## Step 2 — Warm-intro cross-check

Match connections to pipeline account names (normalize spelling and legal
suffixes) and to named champions. Rank: decision-makers at open deals first;
a connection senior to the current champion is highest value. Output a sheet:
Account / Stage / $ / Connection / Title / Suggested move. Finish with the
2–3 intros the user should make this week, each with a one-line draft blurb.

Only claim connections literally present in the CSV — never infer someone
"probably knows" a company. Pipeline data belongs to the company being
reviewed: confidential to this channel, never reused elsewhere.
