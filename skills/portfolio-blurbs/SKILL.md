---
name: Portfolio Blurbs
description: Keep a VC firm's one-paragraph portfolio-company blurbs current. Load the company list into a live sheet, email each founder once a month asking whether their blurb is still right, fold the replies back into the sheet, and hand the firm an always-current snippet library (Superhuman team snippets when possible, a snippets file otherwise). Use when a partner asks to keep company blurbs or descriptions up to date, build a snippet library for the portfolio, or "ask founders to confirm their blurb". Never sends without the person's explicit go-ahead on the batch.
---

# Portfolio blurbs — a monthly loop, not a one-off

The person is a partner at a venture firm with a hundred-odd portfolio
companies. For each one they keep a one-paragraph blurb — what the company
does, who founded it, the stage — and they drop it into emails whenever someone
asks about a company. The blurbs live in Superhuman team snippets, and they go
stale within months. Founders notice, and they mind.

Your job is to own the loop that keeps every blurb current: the list, the
monthly ask to each founder, the replies, the snippet library. The person
approves each batch before it goes out and sees every change before it lands.

## Where things live

| Thing | Where | Why |
|---|---|---|
| The company list | sheet artifact, id `portfolio-blurbs` | live, editable, the one source of truth |
| Change log | sheet artifact, id `blurb-changes` | one row per blurb change, with the founder's exact words |
| Outgoing email text | `/workspace/blurbs/template.md` | the person's voice, edited once |
| Per-cycle state | `/workspace/blurbs/cycles/<YYYY-MM>.json` | who was asked, when, who answered |
| Snippet library | `/workspace/blurbs/snippets.md` plus Superhuman when reachable | the deliverable the firm actually uses |

Sheet columns, in this order: `company, founder_name, founder_email, blurb,
blurb_updated, last_asked, last_reply, status, notes`. `status` is one of
`Current` (confirmed within the window), `Asked` (mail out, no reply yet),
`Stale` (no confirmation for 90+ days), `Changed` (founder sent a new blurb,
awaiting the person's ok), `Skip` (do not email; founder left, company
acquired, person said so).

## Step 0 — File the task, then ask what only they know

`update_task` (InProgress) first, then one `ask_question` card:

1. **Where is the list today?** `choice`: Excel or CSV I'll drop in /workspace /
   Notion page or database (I'll sign in) / Google Sheet (I'll sign in) /
   It's only in Superhuman snippets.
2. **Cadence** `choice`: Monthly on the 1st / Monthly on a day I'll name /
   Quarterly / Just run it once now.
3. **Who signs the email?** `text`. The from-name founders will see.
4. **Superhuman** `yes_no`: "Push confirmed blurbs into Superhuman team
   snippets? I'll drive it in the shared browser once you're signed in."
5. **Confirmation window** `choice`: 60 days / 90 days (default) / 180 days.
   A blurb confirmed inside the window is not re-asked.

Skip anything a file in `/workspace` or an earlier message already answers.
End your turn; the answers reopen the task.

## Step 1 — Load the list into the sheet

Read the `artifacts` skill for the exact commands. Then:

- **File:** read it with the `xlsx` skill. Map columns by meaning, not by
  header: company, founder name, founder email, blurb. Keep any extra columns
  in `notes`.
- **Notion or Google Sheet:** this is browser work on the session the person
  signed in themselves. Read the `browser` skill first. If the site needs a
  sign-in, park with a `forHuman` todo (`humanAction: Computer`) and wait.
  Export to CSV where the site offers it rather than scraping rows.
- **Superhuman-only:** open Settings → Snippets in the shared browser and copy
  each team snippet's name and body out. Slow but bounded; say how many.

`sheet:create` titled "Portfolio blurbs", `sheet:importCsv` the rows, register
it as `portfolio-blurbs`. Create `blurb-changes` empty with the header
`date, company, founder_email, old_blurb, new_blurb, founder_words, applied`.

Rows with no founder email get `status: Skip` and a note. Report the count in
chat and link the sheet: `[Portfolio blurbs](artifact:portfolio-blurbs)`. Park
with one `forHuman` todo: "Check the list. Fix emails, mark Skip where we
shouldn't write." Their edits are the truth; re-read the sheet before every
later step.

## Step 2 — The email, once

Write `/workspace/blurbs/template.md` in the person's voice. Under 90 words.
Shape:

```
Subject: Quick check on {{company}}'s description

Hi {{founder_first}},

Once a month I make sure the one-paragraph description we use for {{company}}
is still right. Here's what we have:

"{{blurb}}"

Still accurate? If not, reply with the version you'd like us to use and I'll
swap it in.

{{signature}}
```

Show it in chat and ask one `yes_no`: use this, or edit the file. No slop:
no "hope this finds you well", no praise, no second ask in the same mail.

## Step 3 — Send a cycle (the person approves the batch)

1. Re-read the sheet. The batch is every row where `status` is not `Skip` and
   `blurb_updated` or `last_reply` is older than the confirmation window, or
   empty.
2. Write `/workspace/blurbs/cycles/<YYYY-MM>.json` with the batch: company,
   email, the exact rendered mail.
3. Post the count and three rendered samples in chat, then `ask_question` one
   `yes_no`: "Send these N?" **Nothing goes out without a yes on the batch.**
4. Sending is browser work in the person's mailbox (Superhuman or Gmail,
   whichever they use), on their signed-in session. Read the `browser` skill.
   Compose, paste, send, one at a time, and mark `last_asked` and
   `status: Asked` on each row **as it goes**, so a stopped run resumes without
   double-sending. A batch over 40 is a worker's job: write a brief with the
   cycle file path and the sheet id, and fork one worker with
   `--sandbox fork`. Never two workers on one mailbox.
5. Never send a second mail to the same founder in one cycle. Never BCC or CC
   anyone. Never attach anything.

## Step 4 — Collect replies (scheduled, not polled)

When the batch is out, `update_schedule` a `once` wake-up 7 days later titled
"Collect blurb replies for <YYYY-MM>", and another at 14 days. The prompt to
your future self: the cycle file path, the sheet id, and the rules below.

On each wake-up, in the mailbox through the browser, search for replies to the
cycle's subject line. For each reply:

- **"Yes / still accurate / looks good"** → `status: Current`,
  `blurb_updated` = today, `last_reply` = today.
- **A new blurb in the reply** → put the founder's exact text in
  `blurb-changes` (`founder_words` verbatim, `new_blurb` = your cleaned
  version: their words, fixed typos, one paragraph, no marketing adjectives
  added), set `status: Changed`. Do **not** overwrite `blurb` yet.
- **A founder left, company acquired, "please stop"** → `status: Skip`, note
  why, and tell the person.
- **Out of office, bounce** → leave `Asked`, note it.

After the 14-day pass, rows still `Asked` become `Stale` if outside the window.
Never send reminders on your own; offer one in the report and let them say so.

## Step 5 — Approve changes, publish snippets

Post a short report and park with `forHuman` todos, one per changed blurb:
"Approve new blurb for {{company}}" with the old and new text in the todo
detail. When they check one:

1. Write `new_blurb` into `blurb`, set `blurb_updated`, `status: Current`, and
   `applied: yes` in `blurb-changes`.
2. Regenerate `/workspace/blurbs/snippets.md`: one `## {{company}}` heading
   and the blurb per company, alphabetical, `Skip` rows omitted. Link it:
   `[Snippet library](sandbox:/workspace/blurbs/snippets.md)`.
3. **Superhuman, if they said yes:** in the shared browser, open Superhuman
   Settings → Snippets, find the team snippet named for the company, replace
   the body, save. Create it if missing. One at a time, verify the saved body
   reads back, mark the change `applied: superhuman`. If Superhuman is not
   signed in, park with a `forHuman` todo (`humanAction: Computer`) rather than
   guessing.

## Step 6 — Make it a habit

Once a full cycle has run, `update_schedule` the recurring send on the cadence
they chose (`monthly`, `monthDay` they named, their timezone) with priority
Background. The prompt restates everything: sheet ids, template path, window,
the approve-the-batch rule, the reply wake-ups. Confirm the schedule in chat.
The recurring run still stops at "Send these N?" every time.

## Reporting

After each cycle, one message: asked N, confirmed N, changed N (with the
approve todos), stale N, skipped N, snippets updated N. Link the two sheets and
the snippets file. Then the accountability lines:

```
Did: sent 41 via Superhuman; 28 replies read.
Didn't: push 3 changed blurbs to Superhuman — awaiting your approval.
Adapted: 2 founders bounced; marked Stale, not re-sent.
```

## Rules

- **The blurb is the founder's.** Their reply text wins over anything you or
  the web would write. Never "improve" a blurb with web research.
- **Every change is traceable.** `blurb-changes` holds the founder's exact
  words for every edit. A blurb with no row there did not change.
- **Approval twice.** Once on the outgoing batch, once per changed blurb.
  Never send, never overwrite, without those.
- **Their sheet edits are the truth.** A row they set to `Skip` stays `Skip`.
  An email they corrected is the one you use.
- Passwords: never ask, never type. Sign-ins happen on the desktop, by them.
