---
name: Weekly Report
description: Build the weekly report — gather the week's meetings, notes, and email; distill; deliver as a doc plus a short chat summary. Use every Monday morning, whenever the user asks for a weekly report or "what did I commit to this week", or when a scheduled task fires for it.
---

# Weekly report & action items

The user's week is back-to-back meetings; their scarcest resources are
attention and follow-through. The report's job is to protect both: they should
walk into Monday knowing what happened, what they committed to, and what needs
them — without rereading anything themselves.

## The window

- "Last week" = previous Monday 00:00 through Sunday 23:59 in the user's
  timezone, unless they name a different range.
- Asked mid-week ("what did I commit to this week"), use Monday of the current
  week through now, and say so.
- Print the resolved date range in the report header.

## Gather (never block on a missing source)

Work through what's available; later sources fill gaps left by earlier ones.

1. **Meeting notes**: read everything new under `/workspace/uploads/granola/`
   (and any notes dropped in the channel) dated in the window.
2. **Email + calendar**: if signed into Gmail/Calendar in the shared browser,
   sweep last week's threads and meetings — capture external commitments in
   both directions ("I'll send you X" / "they'll intro me to Y"), and next
   week's meetings for the prep section. If not signed in, add a to-do for the
   user asking them to sign in once, and continue with what you have.

If a source is unavailable, skip it silently and note it once in a footer line
("Sources: Granola notes, calendar. Gmail not connected."). Never stall the
report waiting on a source.

## Produce

A **doc artifact** (not a chat wall) with, in order:

- **Top of mind** — max 3 bullets: the things that will bite if ignored.
- **This week's meetings** — one line each; skip declined and placeholder
  events.
- **Action items** — deduped across sources, each tagged with its source
  (meeting or thread), the user's own commitments first, then things they're
  waiting on from others.
- **Next week** — one prep line per upcoming meeting.

Every action item must trace to a real source — never invent or pad. Keep the
whole report under one page. Then post a 2-line chat message pointing at the
doc with the one thing that most needs the user today.

## If asked to email it

Draft in Gmail via the browser, show the user the draft, and confirm before
sending — sending email is a consequential action, never silent.
