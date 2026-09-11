---
name: Invoice chaser
description: Chase unpaid invoices every Friday with a short reminder per customer, in the person's voice, after they approve the batch. Use when someone asks to chase, follow up on, or collect overdue invoices, or to set up a weekly collections routine. Never sends without a yes on the batch.
---

# Invoice chaser

The person invoices customers and some invoices go unpaid. Your job is the
weekly loop: know which invoices are overdue, draft one polite reminder each,
get the batch approved, send, and keep a tracker current.

## Where things live

| Thing             | Where                                                           |
| ----------------- | --------------------------------------------------------------- |
| Invoice tracker   | sheet artifact, id `invoice-tracker` (the bundled app seeds it) |
| Reminder template | `/workspace/invoices/template.md`                               |
| Per-week batch    | `/workspace/invoices/batches/<YYYY-MM-DD>.json`                 |

## Step 0 — File the task, then ask

`update_task` (InProgress), then one `ask_question` card. Skip anything a
file in `/workspace` already answers.

1. **Where are the invoices?** `choice`: Stripe (I'll sign in) / A CSV I'll
   drop in /workspace / I'll paste them.
2. **How overdue before we chase?** `choice`: 7 days / 14 days / 30 days.
3. **Who signs the email?** `text`.

End your turn. Answers reopen the task.

## Setup (the bundle)

Teaching this skill queues a setup task for you. Copy `bundle/app` to
`/workspace/app` as the `custom-app` skill describes, start the services,
seed the tracker from the invoices the person pointed you at, and register
the app tab. Create the `invoice-chase` schedule with `--enabled false` and
ask the person to confirm the day and timezone before you enable it.

## Each Friday

1. Re-read the tracker. The batch is every invoice past the overdue window
   with no reminder in the last 7 days.
2. Render one reminder per customer from the template. Write the batch file.
3. Post the count and two samples in chat, then `ask_question` one `yes_no`:
   "Send these N?" Nothing goes out without a yes.
4. Send from the person's mailbox through the browser, one at a time, and
   mark each row `reminded_at` as it goes so a stopped run resumes cleanly.

## Rules

- **The person approves every batch.** No exceptions, no reminders on your own.
- **Their tracker edits are the truth.** A row they mark Paid stays Paid.
- Passwords: never ask, never type. Sign-ins happen on the desktop, by them.
- No person's or company's name lives in this skill; everything specific comes
  from the tracker or the ask card.
