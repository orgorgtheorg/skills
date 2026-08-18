---
name: Outbound Prospecting
description: Run a four-step, human-in-the-loop outbound prospecting workflow — ICP + company list building (Clay-friendly), contact finding, connection-trigger research, and template-based email drafting. Use when the user wants to do outbound, build a prospect list, find who to contact at target companies, or write cold outreach. Never send anything; the human always sends.
---

# Outbound prospecting — four steps, human in the loop

The user runs outbound to sell something. Your job is to be the system, not
the sender: walk them through four steps, one at a time, checkpointing before
you move on. The user makes every judgment call; you do the legwork between
calls. **You never send an email.** The end state of this workflow is a set of
drafts the user reviews and sends themselves.

## Operating rules (read first)

- **Ask with `ask_question`, not with paragraphs.** Every checkpoint and every
  interview question goes through the `ask_question` tool: choice questions
  where a choice exists, short answers otherwise, a few questions at a time.
  It parks the task until they answer and reopens it when they do, so you
  never sit in a loop asking "are you still there". Chat prose is for telling
  them what you found — not for collecting decisions.
- **One step at a time.** Finish and confirm each step before starting the
  next. The user can jump back ("redo step 2 for Acme") at any point.
- **The three lists are spreadsheet Apps, not files.** Companies, contacts and
  triggers each live in the sheet editor, registered as an artifact so the user
  can open, sort and edit them while you work (read the `artifacts` skill for
  the exact commands). Use the stable ids `companies`, `contacts`, `triggers`
  so a later session finds the same tabs.
  - **Their edits are the truth.** Before every step, read the sheets back with
    `sheet:getValues` and work from what is in them now. If they deleted six
    rows, those companies are dead — do not resurrect them, do not argue.
  - Keep the prose next to them in `/workspace/outbound/<campaign-slug>/`:
    `icp.md`, `template.md`, `drafts/<contact>.md`, and `notes.md` for anything
    the user told you that the sheets cannot hold.
- **Run one task per step, and hand the human their turn as todos.** Use
  `update_task` so the step is visible on the board. When it is their move —
  prune the list, grade the triggers, approve a batch — park the task with
  `forHuman` todos naming exactly what you need. Checking the last one reopens
  the task and you continue. Do not park without saying what you are waiting
  for.
- **Anything behind a login is browser work.** LinkedIn, Clay, the mailbox,
  any tool in their stack: drive it with the `computer` tool in the workspace
  browser, on the session the user signed in themselves. If a site wants
  credentials, say so and let them sign in on the desktop — **never ask for a
  password, and never type one.** File the task before the first `computer`
  call; they are watching that screen.
- **Fan out with sub-agents for the slow steps.** Steps 2 and 3 are the same
  job repeated per company, so `spawn_agents` a batch of them — **Builders**,
  because an Explorer has no browser and this work needs one. Four to six
  companies each, up to ten at a time. Give every sub-agent the same return
  contract: rows in the sheet's exact column order, plus a source URL per
  claim, plus "leave blank rather than guess". You merge their rows into the
  sheet; they never write it. One sub-agent coming back empty is a gap to
  report, not a reason to invent.
- **Use what the user already runs.** Clay, Zapier, n8n, their CRM: produce
  inputs and outputs in the shape those tools want (CSV in, CSV out) rather
  than replacing them.
- **Resume gracefully.** On any new message about outbound, read the campaign
  folder and the sheets first, then say which step the campaign is on and
  continue from there.

## Step 1 — ICP and company list

Goal: a target list of companies with light enrichment. The thinking about
who to target is the user's; extracting it is yours.

1. Interview the user with `ask_question` (max ~6 questions, choices where you
   can): what they sell, deal size, who buys it today, best 3 current
   customers and why, disqualifiers (size, geo, industry, stack), and how many
   companies they want in this batch (default 25–50).
2. Write `icp.md`: 5–10 concrete, checkable characteristics ("B2B SaaS,
   20–200 employees, US/EU, has an outbound sales team, hiring SDRs") — not
   vibes ("innovative companies"). If more than one person is in the channel,
   this is the moment to say so: an ICP is worth two people arguing over for
   five minutes.
3. Build the list:
   - **Clay path (preferred if they use Clay):** turn the ICP into a Clay
     table recipe — the exact filters and sources — and either drive it in the
     browser or have them run it and drop the CSV back in the channel. Import
     it into the companies sheet.
   - **No-Clay path:** build the list yourself with web search and the
     browser, against the ICP characteristics. Be honest about confidence;
     mark rows you are unsure of.
4. Light enrichment only at this stage: company name, domain, size, industry,
   one-line "why they fit", and — where cheaply available — a generic contact
   pattern (e.g. first.last@domain). Deep person-level work belongs to step 2.
5. Checkpoint: register the companies sheet, tell them it is open, and park
   with a `forHuman` todo — kill the rows that feel wrong. A pruned list of 30
   beats an unpruned 200.

## Step 2 — Find the right person

Goal: one primary (and optionally one backup) human per company.

1. Ask which titles have bought from them before, and who tends to be the
   blocker. Turn that into a title priority list (e.g. "VP Sales > Head of
   Growth > CEO at <50 employees").
2. Split the surviving companies across Builder sub-agents. Each one finds its
   people from the company site, LinkedIn, podcasts, conference speaker lists
   and blog bylines, and returns: company, name, title, profile URL,
   best-guess email, and `guessed` or `verified`.
3. Where the person's feed is reachable, skim the last few months and record
   in one line **what they seem to care about or struggle with** — in their
   words, with a link to the post. No feed access? Leave it blank; never
   invent it.
4. Merge the rows into the contacts sheet as they come back, so the user
   watches it fill.
5. Checkpoint: park with `forHuman` todos — confirm, swap, or ask for a backup
   at named companies.

## Step 3 — Connection-trigger research

Goal: for each contact, **the best reason this outreach isn't cold**. This is
not company research for its own sake — it is finding the hook. Work the three
trigger types in this order and record the strongest one found:

1. **Mutual connection / shared thing.** A person both sides know, a shared
   community, past employer overlap, an event both attended. Ask up front for
   their raw material — connections export, schools, past companies, cities,
   communities, hobbies — and cross-reference it against every contact. This
   tier is the whole reason the user is in the loop; nobody else has this data.
2. **Firm trigger.** What the company is going through and what this person
   owns inside it: funding round, new market, hiring surge on a relevant team,
   public complaint, new leadership, product launch — anything that creates the
   problem the user's product solves. Cite the source.
3. **Human connection.** Same school, same hometown, shared interest, a post
   worth genuinely engaging with. Weakest of the three; use it when the first
   two come up empty, and keep it tasteful — public information only, nothing
   that reads as surveillance.

Fan this out the same way as step 2, one batch of contacts per Builder. Fill
the triggers sheet: contact, trigger type, the trigger in one sentence, source
link, and a suggested first line **in plain language, not copy**.

A contact with no trigger stays in the sheet with an empty trigger and is
reported as such. Do not manufacture a hook to fill a cell — that is the exact
failure this step exists to prevent.

Checkpoint: park with `forHuman` todos and have them grade the triggers —
good / weak / creepy. Drop anything they call creepy without argument.

## Step 4 — Writing, the anti-slop phase

Most AI outbound fails because the AI wrote too much of it and it shows.
Invert the ratio: **the user's voice is the template; the research fills the
slots.**

1. Get a template. If they have emails that worked, start from those — read
   them out of their sent mail in the browser if that is where they live.
   Otherwise co-write one, interview-style with `ask_question`: opener style,
   how they reference the trigger, one-line pitch, the ask. Under 120 words,
   3–5 variables like `{{first_name}}`, `{{trigger_line}}`,
   `{{company_specific}}`. Save as `template.md`.
2. Merge template × list: fill the variables per contact from the triggers
   sheet. The trigger line must be specific enough that the email could not be
   sent to anyone else.
3. Slop check every draft before you show it. Rewrite or flag anything with:
   - "I hope this email finds you well", "I came across your profile", "I was
     impressed by", "In today's fast-paced world"
   - flattery without specifics, or three adjectives doing one adjective's job
   - em-dash-studded LinkedIn-brochure rhythm; sentences the user would never
     say out loud
   - any claim about the prospect you cannot point to a source for

   The bar: would a busy stranger believe a human wrote this specifically for
   them? If not, it does not go in the batch. Say how many you rejected and
   why — the rejects are evidence the bar is real.

4. Review in batches of ~5. They edit or approve. Approved drafts go to
   `drafts/`, and into their **mail drafts folder** through the browser.
   **The user sends manually. Always.** Do not schedule sends, do not
   auto-follow-up. If they ask you to send, put it in drafts and tell them it
   is ready.

## Keep it running

Once a campaign has been through all four steps, offer to make it a habit:
`update_schedule` a weekly run that takes the next batch of companies through
steps 1–3 and leaves graded triggers waiting, so their Monday starts at the
writing step. Never schedule anything that writes to their mailbox — the
recurring work stops at drafts, same as the manual work.

## What done looks like

The three sheets current and edited by the user, `icp.md` and `template.md` in
the campaign folder, every approved draft in `drafts/` and in their mail
drafts, and a short closing summary: how many companies in, how many survived
their pruning, how many contacts found, the trigger-quality breakdown, how
many drafts failed the slop check, and which drafts are ready to send.
