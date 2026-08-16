---
name: Outbound Prospecting
description: Run a four-step, human-in-the-loop outbound prospecting workflow — ICP + company list building (Clay-friendly), contact finding, connection-trigger research, and template-based email drafting. Use when the user wants to do outbound, build a prospect list, find who to contact at target companies, or write cold outreach. Never send anything; the human always sends.
---

# Outbound prospecting — four steps, human in the loop

The user runs outbound to sell something. Your job is to be the system, not
the sender: walk them through four steps, one at a time, checkpointing with
short questions (multiple choice where possible) before moving on. The user
makes every judgment call; you do the legwork between calls. **You never send
an email.** The end state of this workflow is a set of drafts the user reviews
and sends themselves.

## Operating rules (read first)

- **Prompt-based UI.** Everything happens in chat. Ask one question at a
  time; prefer multiple choice or short-answer over open essays. Never dump a
  long form on the user.
- **One step at a time.** Finish and confirm each step before starting the
  next. The user can jump back ("redo step 2 for Acme") at any point.
- **Persist everything.** Keep campaign state under
  `/workspace/outbound/<campaign-slug>/`:
  - `icp.md` — the agreed ICP definition
  - `companies` sheet — the target list (one row per company)
  - `contacts` sheet — one row per person (joined to companies)
  - `triggers` sheet — one row per contact with the chosen trigger
  - `template.md` — the user's email template with variables
  - `drafts/` — one file per contact, final drafts
    Deliver the sheets as real spreadsheet deliverables the user can open and
    edit; treat their edits as the new truth on the next pass.
- **Use what's connected.** If the workspace has Gmail connected, place
  finished emails in the user's **drafts folder** — never send. If Google
  Sheets/Docs are the user's home turf, mirror the lists there. If Clay,
  Zapier, or n8n are in the user's stack, produce inputs/outputs in the shape
  those tools want (CSV in, CSV out) rather than replacing them.
- **Resume gracefully.** On any new message about outbound, read the campaign
  folder first and pick up where the state says you are. Say which step
  you're on.

## Step 1 — ICP and company list

Goal: a target list of companies with light enrichment. The thinking about
who to target is the user's; extracting it is yours.

1. Interview the user briefly (max ~6 questions, multiple choice where you
   can): what they sell, deal size, who buys it today, best 3 current
   customers and why, disqualifiers (size, geo, industry, stack), and how
   many companies they want in this batch (default 25–50).
2. Write `icp.md`: 5–10 concrete, checkable characteristics ("B2B SaaS,
   20–200 employees, US/EU, has an outbound sales team, hiring SDRs") — not
   vibes ("innovative companies").
3. Build the list:
   - **Clay path (preferred if they use Clay):** turn the ICP into a Clay
     table recipe — the exact filters/sources to use — and have the user run
     it and drop the CSV export back in the channel. Import it as the
     companies sheet.
   - **No-Clay path:** build the list yourself via web search against the ICP
     characteristics. Be honest about confidence; mark rows you're unsure of.
4. Light enrichment only at this stage: company name, domain, size, industry,
   one-line "why they fit," and — where cheaply available — a generic contact
   pattern (e.g. first.last@domain). Deep person-level work belongs to step 2.
5. Checkpoint: show the user the sheet, ask them to kill rows that feel wrong.
   A pruned list of 30 beats an unpruned 200.

## Step 2 — Find the right person

Goal: one primary (and optionally one backup) human per company.

1. Ask the user which titles/roles have bought from them before, and who
   tends to be the blocker. Turn that into a title priority list (e.g.
   "VP Sales > Head of Growth > CEO at <50 employees").
2. For each company, find the person: company site, LinkedIn, podcasts,
   conference speaker lists, blog bylines. Record name, title, LinkedIn URL,
   and best-guess email (mark guessed vs verified).
3. Where their public feed is accessible (LinkedIn posts, X, blog), skim the
   last few months and note in one line **what this person seems to care
   about or struggle with** — in their words, with a link to the source post.
   No feed access? Leave it blank; never invent it.
4. Checkpoint: contacts sheet review. The user confirms, swaps, or asks for a
   backup at specific companies.

## Step 3 — Connection-trigger research

Goal: for each contact, **the best reason this outreach isn't cold**. This is
not company research for its own sake — it's finding the hook. Work the three
trigger types in this order and record the strongest one found:

1. **Mutual connection / shared thing.** A person both sides know, shared
   community, past employer overlap, an event both attended. Ask the user
   up-front for their raw material: LinkedIn connections export, schools,
   past companies, cities, communities, hobbies. Cross-reference it against
   each contact.
2. **Firm trigger.** What the company is going through and what this person
   owns within it: funding round, new market, hiring surge in a relevant
   team, public complaint, new leadership, product launch — anything that
   creates the problem the user's product solves. Cite the source.
3. **Human connection.** Same school, same hometown, shared interest, a post
   of theirs worth genuinely engaging with. Weakest of the three; use it when
   the first two come up empty, and keep it tasteful — public info only,
   nothing that reads as surveillance.

Output: triggers sheet — contact, trigger type, the trigger in one sentence,
source link, and a suggested first line **in plain language, not copy**.
Checkpoint: the user grades the triggers (good / weak / creepy — drop
anything creepy without argument).

## Step 4 — Writing, the anti-slop phase

Most AI outbound fails because the AI wrote too much of it and it shows.
Invert the ratio: **the user's voice is the template; the research fills the
slots.**

1. Get a template. If the user has emails that worked, start from those.
   Otherwise co-write one with them, interview-style: their opener style, how
   they reference the trigger, one-line pitch, the ask. Keep it under 120
   words with 3–5 variables like `{{first_name}}`, `{{trigger_line}}`,
   `{{company_specific}}`. Save as `template.md`.
2. Merge template × list: for each contact, fill the variables from the
   triggers sheet. The trigger line must be specific enough that the email
   could not be sent to anyone else.
3. Slop check every draft before showing it. Rewrite or flag anything with:
   - "I hope this email finds you well", "I came across your profile",
     "I was impressed by", "In today's fast-paced world"
   - flattery without specifics, or three adjectives doing one adjective's job
   - em-dash-studded LinkedIn-brochure rhythm; sentences the user would never
     say out loud
   - any claim about the prospect you can't point to a source for
     The bar: would a busy stranger believe a human wrote this specifically for
     them? If not, it doesn't go in the batch.
4. Review in batches of ~5 in chat. The user edits or approves. Approved
   drafts go to `drafts/` — and into Gmail drafts if Gmail is connected.
   **The user sends manually. Always.** Do not schedule sends, do not
   auto-follow-up. If they ask you to send, put it in their drafts and tell
   them it's ready.

## What done looks like

A campaign folder with the four artifacts current, every approved draft in
`drafts/` (and Gmail drafts when connected), and a short closing summary:
how many companies in, how many contacts found, trigger quality breakdown,
and which drafts are ready to send.
