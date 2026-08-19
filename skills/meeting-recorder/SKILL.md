---
name: Meeting Recorder
description: Join a scheduled video call in the workspace browser, record the audio, capture a live transcript, and write the notes and follow-ups afterwards. Works with Google Meet, Zoom, Microsoft Teams and Webex, and can be figured out for anything else. Use when the user wants a meeting recorded, transcribed, summarised, or wants notes and action items from a call.
---

# Meeting recorder — join, record, write it up

The user wants a meeting captured. You sit in the call from the workspace
browser, record what is said, and afterwards produce notes they can use.

Four things make this possible, and all four already exist. Do not rebuild them:

| What                | How                                                                                                                                                               |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hearing the call    | The sandbox has a speaker and a microphone (PulseAudio null devices). Chrome plays the meeting into the `speaker` sink.                                           |
| Recording           | `orgspace-record start <slug>` / `stop` — 16 kHz mono Opus into `/workspace/Recordings`.                                                                          |
| The transcript      | The platform's own live captions, tailed into a file by `scripts/capture-captions.js`. The sandbox holds no speech-to-text key, thus captions are the transcript. |
| Being there on time | `update_schedule` with `freq: once`. Time is the only thing that can start you; you cannot sit and wait.                                                          |

## Hard rules

- **Say that you are recording, in the meeting, before you record.** Post it in
  the meeting chat as your first act after joining. Many places require every
  participant's consent, and this is not a rule you get to weigh against
  convenience. If the host or anyone else objects, stop the recording, say so in
  the channel, and take notes from captions only.
- **Never ask for a password, and never type one.** When a service wants a
  sign-in, the human does it on the shared desktop. That is what the take-over
  ask below is for.
- **Never invent what was said.** The transcript is captions, and captions drop
  words, mangle names and miss the person with the bad microphone. Write notes
  only from lines you actually captured. When a section is too garbled to use,
  say so in the notes and point at the timestamp in the recording.
- **Never sit in a loop waiting.** A meeting is an hour; your turn is not. You
  join, start the capture, end your turn, and a scheduled task wakes you to wrap
  up. Polling a call for an hour burns the session and gets you nothing.

## Before the meeting

Do this the moment the user asks, not at meeting time. The sign-in check is the
whole reason: an ask that lands two minutes before the call is an ask the human
cannot answer in time.

1. **Get the details.** You need the join URL, the start time with a timezone,
   the expected duration, and who is in it. If the user gave you a calendar
   invite or a link, read it. If anything is missing, `ask_question` — one card,
   choices where there are choices. If they pointed you at a calendar, open it
   with the `computer` tool and read the event.

2. **File the task.** `update_task` with a stable id like
   `record-<meeting-slug>`, the spec holding the URL, the time and the platform.
   Everything below updates this one task, thus the user watches one card rather
   than a stream of chat.

3. **Check the sign-in NOW — this is the pre-flight.** Open the join URL in the
   workspace browser with the `computer` tool and look at what the page offers.
   Do not join yet; you are only asking "will this let me in when the time
   comes?".
   - Signed in and the meeting accepts you → say so and go to step 4.
   - A sign-in wall, an account chooser, an SSO prompt, a "join from your
     browser" that demands an account → **park for a take-over**, below.

4. **Schedule the join.** `update_schedule` with `freq: once` and `at` set to
   **two minutes before** the start, in ISO 8601 with the offset. The `prompt`
   is a letter to your future self and must stand alone — the URL, the platform,
   the recording slug, the task id, the expected end time, and the instruction
   to follow this skill. Your future self has no memory of this conversation
   beyond the channel.

5. **Schedule the wrap-up too**, `freq: once` at the expected end plus five
   minutes. If the meeting runs long you can push it; if you never schedule it,
   nothing ever stops the recording.

### The take-over ask — when there is no signed-in identity

This is the case the user cares most about, so make it precise and make it
early. Park the task:

```
update_task
  taskId: record-<meeting-slug>
  status: Blocked
  blockedReason: TakeOverBrowser
  detail: "Sign in to Zoom on the workspace desktop so I can join Thursday's 2pm call."
  todos: [{ todo: "Sign in to Zoom in the shared browser", checked: false,
            forHuman: true, humanAction: Computer }]
```

That produces one card: **"needs you at the computer"**, with a button that
takes them straight to the shared desktop. What matters:

- `detail` is a **second-person instruction naming the one thing to do** — "Sign
  in to Zoom on the workspace desktop", never "I was unable to authenticate".
  The user reads this sentence and acts on it; it is not a status report.
- Leave the browser **on the sign-in page** you want them to land on. They
  should arrive and see the prompt, not a blank tab.
- Park **before** you need it, not at join time. Say in the detail which meeting
  it unblocks and when it is, so they can judge the urgency themselves.
- Checking their todo, or answering in chat, reopens the task and wakes you.
  When you come back, verify the sign-in really took, then carry on at step 4.
- If the meeting starts and the sign-in never happened, do not silently miss it.
  Say in the channel that you could not join and why, and leave the task parked.

Use the same shape whenever the call itself needs a human: a waiting room that
never admits you, a passcode you were not given, a 2FA prompt mid-join, a
"host must admit you" that times out.

## Joining and recording

Your scheduled task fires. Work the task, and be quick — you are two minutes out.

1. Open the join URL with `computer`. Join **muted, camera off**, always.
2. Set a display name that says what you are, if the platform lets you before
   joining — "<Agent name> (recording)". People deserve to know what the extra
   participant is.
3. **Announce the recording in the meeting chat.** One line: who you are, that
   you are recording and transcribing for the user, and how to ask you to stop.
4. **Turn on the platform's live captions.** This is the transcript, so do not
   skip it. Per-platform steps are below.
5. Start the recording:
   `bash: orgspace-record start <meeting-slug>`
6. Start the caption capture, **in the background** (`run_in_background: true`):
   ```
   node /.skills/meeting-recorder/scripts/capture-captions.js \
     --url <host-substring> --out /workspace/Recordings/<slug>.txt
   ```
   Keep the handle it returns; that is what you stop later.
7. Check it is working before you walk away: wait ~30s, `read` the transcript
   file, confirm lines are arriving. If it is empty, fix it now (see below) —
   an hour of silent nothing cannot be recovered afterwards.
8. `update_task` to InProgress with a detail like "Recording — transcript at
   /workspace/Recordings/<slug>.txt", then **end your turn**.

### If the transcript file stays empty

In order:

1. Are captions actually on in the meeting UI? This is the usual answer.
2. Run the probe, which prints what the live regions on the page really are:
   `node /.skills/meeting-recorder/scripts/capture-captions.js --url <host> --probe`
3. Re-run the capture with the selector the probe showed:
   `--selector '<css>' --speaker '<css>' --text '<css>'`
4. Write what worked into `/workspace/memory/general/meeting-<platform>.md`, with
   the date. These selectors change without notice; the file is how the next
   meeting starts from your answer instead of this ladder.

The audio recording is independent of all this. It keeps running even when
captions fail, thus you always have something.

## Per-platform

### Google Meet — `meet.google.com`

- Needs a signed-in Google account. Check it early; an account chooser is the
  common blocker.
- Join: open the link, camera and mic off, **Join now**. If it says **Ask to
  join**, you are in a waiting room — press it, tell the user in the channel
  that you are waiting to be admitted, and park for a take-over if nobody lets
  you in within a few minutes.
- Captions: the **CC** button in the bottom bar, or the three-dot menu →
  **Captions**. English is the default; set the language if the meeting is not
  in English.
- Chat for the announcement: the **Chat with everyone** panel, right side.
- Meet caption lines only hold the last few speakers on screen, which is exactly
  what the capture script is built for. Leave it running.

### Zoom — `zoom.us`

- Prefer the **web client**. A link opens the desktop app by default and the
  sandbox has none: take the **Join from your browser** link on the launch page.
  If the host disabled the web client, that is a hard stop — tell the user, do
  not fight it.
- Sign-in is often required for the web client. This is the platform most likely
  to need the take-over ask, so check it first.
- Join: name yourself, **Join Audio by Computer** — without this you are in the
  meeting but silent, and the recording is empty.
- Captions: **Show Captions** / **Live Transcript** in the bottom bar. Only the
  host can enable live transcription for the meeting; if the control is missing,
  ask the user to ask the host, and fall back to the audio recording alone.
- Waiting rooms are common. Same rule: say you are waiting, then park.

### Microsoft Teams — `teams.microsoft.com` / `teams.live.com`

- Use **Continue on this browser**. Teams pushes its app hard; the browser path
  works.
- A work or school account usually means SSO, which usually means the take-over
  ask. Guest join without an account exists for some meetings — try it before
  you park.
- Join: mic and camera off, **Join now**. Lobby behaviour is the same as a
  waiting room.
- Captions: **More** (…) → **Language and speech** → **Turn on live captions**.
- Teams renames its caption DOM more often than the others. Expect the probe
  step, and write the answer to memory when you find it.

### Webex — `webex.com`

- **Join from your browser** avoids the desktop app.
- Many Webex meetings need only a name and email, thus no sign-in — try before
  you park.
- Captions: the **CC** button, or **More options** → **Show captions**. The host
  may have to enable it.

### Anything else

Every primitive is generic; nothing above is special to these four. For a
platform you have not seen:

1. Open the join page and read it with `computer`. Decide the same three things:
   does it need an account, does it run in the browser, does it have captions?
2. No account needed → join and carry on. Account needed → the take-over ask,
   unchanged.
3. Start `orgspace-record` regardless. Audio capture is platform-blind: it
   records whatever Chrome plays, thus it works before you have solved anything
   else.
4. For captions, turn them on in the UI, then run the capture script with
   `--probe` to find the container and `--selector` to use it. The script has no
   knowledge of the platform beyond a default selector list.
5. If the platform has no captions at all, say so plainly. You will deliver a
   recording and notes from what you could hear, not a transcript.
6. Write what you learned to `/workspace/memory/general/meeting-<platform>.md`:
   the join path, the caption control, the selectors, the traps. Next time this
   section is not needed.

## After the meeting

The wrap-up task fires. If the meeting is still going (check the tab), push the
schedule out and end your turn.

1. `task_stop` the caption capture, then `bash: orgspace-record stop`. It prints
   the file path.
2. Leave the meeting properly — hang up, do not just close the tab.
3. `read` the transcript. Write notes to
   `/workspace/Recordings/<slug>-notes.md`: what was decided, what is open, who
   owes what by when, and the questions nobody answered. Attribute by speaker
   where the captions gave you one. Quote a line where the exact words matter.
4. File the follow-ups as real tasks with `update_task` — one per action item
   the user owns. An action item that lives only in a notes file is a note, not
   a follow-up.
5. Post a short summary in the channel: the decisions, the action items, and
   links to the notes, the transcript and the audio. Keep it to what someone who
   missed the meeting needs.
6. Mark the recording task **Done**, with a detail naming the files.
7. Say what you missed. A stretch the captions lost, a speaker who never
   resolved to a name, ten minutes where you were in the waiting room — the user
   needs to know which parts of the notes are thin.
