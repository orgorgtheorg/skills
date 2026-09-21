---
name: sprint-execute
description: Execute a planned sprint by handing it to the current Claude session's model, gpt-5.5, or gemini. Use whenever the user wants to start, run, work, or implement a sprint, kick off sprint execution, or do the work in a SPRINT-<slug>-YYYYMMDD-HHmm plan. Lets the user pick the implementer model, updates the ledger (status + executor) to track progress, and instructs the executor to check off `- [ ]` boxes as tasks are completed.
---

# Sprint Execute

The companion to `sprint-planner`. A planner sprint produces a checkbox plan at `docs/sprints/<slug>/{SID}.md`; this skill picks the sprint, the implementer, and runs the work — then keeps the ledger honest about who did what and where it stands.

Sprints are namespaced per git user (id = `SPRINT-<slug>-YYYYMMDD-HHmm`). By default you operate on **your own** sprints; you can resume anyone's by id. The id's slug tells the ledger which user's `docs/sprints/<slug>/` subtree owns the plan and its ledger row — use `ledger.py paths {SID}` to locate the plan file rather than hand-building the path.

## What this skill is and is not

- **Is**: a controlled handoff. It picks a sprint plan, picks an implementer model (this session's Claude model / gpt-5.5 / gemini), updates the ledger, and runs the implementer with instructions to tick off `- [x]` checkboxes as it goes.
- **Is not**: a multi-model merge. Unlike `sprint-planner`, only **one** model executes — the others would just collide on the same files. The choice of model is the user's call, not a vote.

## Workflow

### 1. Pick the sprint

Default to **your** most-recent sprint with status `in-progress` (resuming work) or, failing that, `planned` (starting fresh). If the user named a sprint id explicitly, use that.

```bash
LEDGER=.claude/skills/sprint-planner/scripts/ledger.py
python3 $LEDGER list --mine --status in-progress     # resume your in-flight work
python3 $LEDGER list --mine --status planned         # or start one you've planned
# To resume or inspect ANYONE'S sprint (not just yours):
python3 $LEDGER list --all
```

If multiple candidates exist and the user didn't specify, ask which one. Verify the plan file exists before going further — `python3 $LEDGER paths {SID}` prints its path (`docs/sprints/<slug>/{SID}.md`); no plan, no execution.

### 2. Pick the implementer

First determine `{SESSION_MODEL}`: the lowercase family name of the model running _this_ session. You know your own model — take it from your context (e.g. `fable`, `opus`, `sonnet`). Never assume `opus`; label the option with the model the session actually runs.

Ask the user via `AskUserQuestion` which model should implement (single question, three options):

- **{SESSION_MODEL} (this session)** — runs in _this_ Claude Code session. Use when the user wants tight oversight, fine-grained control, or interactive course-correction.
- **gpt-5.5** — dispatched via the `codex` CLI in YOLO mode. Use for autonomous bulk execution; trades interactivity for throughput.
- **gemini** — dispatched via the `gemini` CLI in YOLO mode. Use as an alternative autonomous implementer (different model, different blind spots).

If the user has already said which one in their original message, skip the question.

### 3. Mark the ledger

Atomically reflect the choice before any work begins:

```bash
python3 $LEDGER set-status   {SID} in-progress
python3 $LEDGER set-executor {SID} {SESSION_MODEL|gpt-5.5|gemini}
```

For the in-session path, record `{SESSION_MODEL}` (e.g. `fable`, `opus`) — the ledger accepts any model name.

These route to the owning user's ledger by the id's slug, so resuming a teammate's sprint updates _their_ ledger correctly. The ledger is the source of truth for "who is currently working on what". Set it _before_ dispatch so a crash mid-run still leaves an accurate trail.

### 4. Run the implementer

The plan path is `docs/sprints/<slug>/{SID}.md` (resolve it once with `python3 $LEDGER paths {SID}`). Wherever the prompts below say `{PLAN}`, substitute that literal resolved path.

**If the plan cites a research corpus** (`[C23]`, `[S5]` style ids, or a `docs/research-index/...` path), obey `docs/adr/research-corpus-storage.md`:

- Resolve an id to its title and URL in `docs/research-index/<corpus>/INDEX.md` or `manifest.json`. Those are committed, so they resolve for every implementer.
- The full page text is local-only at `~/research/<corpus>/`. It may be absent. `docs/research-index/outbound-sales/restore.sh` re-downloads that corpus; other corpora list their URLs but ship no fetcher. Never block a task on a missing body: the plan's own digest plus the source URL is enough.
- When the implementation bakes in a researched number, **write the figure and the URL into the code comment**, not a corpus path. A tracked file must never depend on a `~/research/...` path.

#### 4a. {SESSION_MODEL} (this session)

You are the implementer. Read `{PLAN}` in full. Then work the checkboxes top-to-bottom:

1. Pick the next unchecked `- [ ]` task.
2. Implement it. If a task is bigger than expected, split it in your head — don't rewrite the plan unless the user asks.
3. As soon as a task is genuinely done (code written, tested where applicable), edit the plan file to flip `- [ ]` → `- [x]` for that line. Don't batch the check-offs at the end — the file is the live progress signal.
4. If you hit a blocker that requires a user decision (ambiguous spec, missing access, scope question), stop and ask. Don't guess your way past a real fork in the road.
5. Use `TaskCreate`/`TaskUpdate` to mirror the sprint tasks if it helps you stay coherent across many tasks. Optional but recommended for sprints with >5 tasks.
6. When you tag the work in a code comment, commit subject, test name, or `## Blockers` note, cite the **full** id `{SID}` (`SPRINT-<slug>-YYYYMMDD-HHmm`) verbatim — never shorten it to `SPRINT-…` without the slug. The slug is what keeps the reference unambiguous across developers.

When all checkboxes are `[x]` (or the user calls it done), proceed to step 5.

#### 4b. gpt-5.5 (codex)

Dispatch in YOLO mode. The CLI is verified — don't second-guess the flags:

```bash
codex exec --dangerously-bypass-approvals-and-sandbox "<prompt>" < /dev/null
```

Close stdin. In the Claude Code Bash tool, codex otherwise waits for the open stdin pipe and never starts.

Prompt (substitute the literal `{SID}` and `{PLAN}`):

> You are implementing sprint **{SID}**. The plan is at `{PLAN}`. Read it in full first.
>
> Work the `- [ ]` checkboxes top-to-bottom. For each task: implement it, then immediately edit the plan file to flip that line's `- [ ]` to `- [x]` so progress is visible on disk. Do not batch the check-offs.
>
> Whenever you reference this sprint in a code comment, commit subject, test name, or `## Blockers` note, cite the full id `{SID}` verbatim — never shorten it. The id carries the author namespace and must stay intact.
>
> Stay within the sprint's scope — non-goals in the plan are non-goals. If you hit a real blocker (ambiguous requirement, missing access, decision the plan didn't make), stop and write a short note at the bottom of the plan under a `## Blockers` heading, then exit. Otherwise, keep going until every checkbox is `[x]`.
>
> Do not modify the ledger; the orchestrator handles that. Do not touch the `drafts/` dir beside the plan — those are historical.

#### 4c. gemini

Same shape, different CLI:

```bash
gemini -y --skip-trust -p "<prompt>"
```

Newer gemini CLIs (0.53 and later) stop with "not running in a trusted directory" when `--skip-trust` is absent.

Use the same prompt as 4b, just substituting the agent self-identifier if you'd like.

### 5. Reconcile and close out

When the implementer returns (or you finish, in the in-session case):

1. Re-read `{PLAN}`. Count remaining `- [ ]` boxes.
2. If zero unchecked **and** no `## Blockers` section was added: mark done.
   ```bash
   python3 $LEDGER set-status {SID} done
   ```
3. If there are remaining unchecked boxes or a blockers note: leave status at `in-progress` and surface the gap to the user. Don't auto-mark done on partial work — the ledger is supposed to reflect reality.
4. Leave the `executor` field set. It's a record of who ran the sprint, not just a current-lock; future re-runs by a different model would overwrite it via `set-executor`.

### 6. Report back

One short message: which sprint, which implementer, how many tasks were checked off vs. left, and any blockers. Don't re-dump the plan — point at the file.

## Ledger fields used by this skill

| Field      | Meaning                                                                                                                                                              |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `status`   | `planned` → `in-progress` (on dispatch) → `done` (on full completion). Stays `in-progress` if any checkboxes remain.                                                 |
| `executor` | The session's Claude model name (e.g. `fable`, `opus`), `gpt-5.5`, or `gemini`. Set on dispatch. The `set-executor` subcommand on `ledger.py` accepts `""` to clear. |

Other fields (`id`, `owner`, `title`, `created`, `updated`) are managed by `ledger.py` automatically.

## Notes and edge cases

- **Whose sprint is it.** `list --mine` (default) shows only your sprints. To resume or inspect a teammate's, use `list --all` and pass the full id — the `set-*` commands route to the owner's ledger automatically via the id's slug.
- **Resuming an in-progress sprint.** If the chosen sprint is already `in-progress` with an executor set, ask the user whether they want to continue with the same model (the natural default) or switch. Switching mid-sprint is fine — just call `set-executor` again — but flag it so the user knows the running history is mixed.
- **Plan file missing.** If the plan file (`paths {SID}`) doesn't exist, refuse to proceed and suggest running `sprint-planner` first. Don't synthesize a plan on the fly — that's a different skill's job.
- **Plan with no checkboxes.** If the plan exists but has no `- [ ]` tasks, the planner output is malformed. Surface to the user; don't paper over it.
- **Don't touch drafts.** The `drafts/` dir beside the plan (`docs/sprints/<slug>/drafts/`) is the planner's historical scratch and is gitignored. Execution operates only on the merged `{SID}.md`.
- **Don't delegate the in-session path.** When the session model is chosen, _this_ session does the work. Don't shell out to `claude -p` — that would lose the conversation context the user is steering from.
- **Codex/gemini are headless.** They run non-interactively. If they need a decision, the prompt above tells them to write a `## Blockers` section and exit. Don't try to make them interactive.
