---
name: sprint-planner
description: Multi-model sprint planning. Use this whenever the user wants to plan a sprint, draft a sprint, kick off sprint planning, create a SPRINT plan, or asks for a sprint plan / sprint doc — even phrased casually ("let's plan the next sprint", "draft a sprint for X"). Orchestrates codex, gemini, and claude CLIs to produce independent drafts, cross-critiques, and a merged final plan under docs/sprints/<your-git-slug>/, and updates the per-user sprint ledger.
---

# Sprint Planner

Given a concentrated **intent** from the user (a paragraph describing what the sprint should accomplish), produce a merged sprint plan at `docs/sprints/<slug>/{SID}.md` built from three independent drafts (codex, gemini, claude) and three cross-critiques, and record the sprint in the per-user YAML ledger.

Sprints are **namespaced per git user** so multiple developers and multiple git worktrees can plan concurrently without colliding, and the per-user ledgers + final plans are **committed to git**. The slug (from `git config user.name`) is baked into the sprint id — `SPRINT-<slug>-YYYYMMDD-HHmm` — so a bare id reference in a code comment or commit is never ambiguous about whose sprint it is.

## Why multi-model?

One model's sprint plan reflects one model's blind spots. Three independent drafts surface a wider set of tasks, risks, and sequencing ideas. Cross-critiques force each model to defend its choices against peers, exposing weak assumptions. The Opus merge step then synthesizes the strongest version — not the average, the best of each.

## Layout

Each developer owns a subtree keyed on their git-user slug. **The per-user `ledger.yaml` and the final `SPRINT-<slug>-…md` plans are committed to git; only `drafts/` is gitignored.**

```
docs/sprints/<slug>/                              # e.g. docs/sprints/wayne-crosby/
├── ledger.yaml                                   # tracked — your ledger (you only ever edit your own)
├── SPRINT-<slug>-YYYYMMDD-HHmm.md                # tracked — merged final plans
└── drafts/                                       # gitignored — LLM scratch
    ├── SPRINT-<slug>-YYYYMMDD-HHmm-CODEX.md       # draft from codex
    ├── SPRINT-<slug>-YYYYMMDD-HHmm-GEMINI.md      # draft from gemini
    ├── SPRINT-<slug>-YYYYMMDD-HHmm-CLAUDE.md      # draft from claude
    └── ...-critique.md                           # the three cross-critiques
```

The id (`SID`) is `SPRINT-<slug>-YYYYMMDD-HHmm` (local time, minute precision). Don't hand-build paths — ask the CLI: `ledger.py paths {SID}` prints the plan path, drafts dir, and ledger for any id.

## Workflow

Follow these phases in order. Don't skip, don't parallelize across phases, but **do parallelize within phases** where noted — the three drafts are independent, and so are the three critiques once drafts exist.

### 1. Capture the raw intent

If the user's request is vague ("plan a sprint"), ask for a concentrated intent paragraph: the goal, rough scope, and any non-negotiables. If they've already given you one, proceed straight to the interview. Don't clarify here — the interview phase does that work.

### 2. Interview to sharpen the intent

Three independent drafts amplify whatever ambiguity is in the intent. A fuzzy intent produces three fuzzy (and divergent) plans, and the merge can't rescue that. Spend one round here to pin down scope before spending three CLI calls.

**Read the repo first.** Skim the obvious context — top-level `README.md`, `CLAUDE.md` if present, your ledger (`ledger.py list --mine`) for recent sprint history, and any files the intent explicitly names. The interview should ask things you _can't_ infer from the repo, not things you were too lazy to look up.

**Ask in one batched round**, not a back-and-forth. Use the `AskUserQuestion` tool with 2–5 questions covering whichever of these are genuinely ambiguous for this intent:

- **Scope boundary** — what's explicitly _out_ of scope? (The single highest-leverage question — drafts otherwise balloon.)
- **Success signal** — what does "done" look like concretely? A merged PR? A metric moving? A demo?
- **Sequencing constraint** — any task that must land first, or any dependency on other teams / sprints?
- **Non-negotiables** — tech choices, patterns, or files that are fixed vs. open for the drafters to decide.
- **Size / timebox** — rough sprint length or effort ceiling, if the user has one in mind.
- **Known risks or prior attempts** — anything that's already been tried, or landmines the drafters should know about.

Skip questions the raw intent already answers. If the intent is already crisp (explicit scope, clear success criteria, named constraints), the interview can be a single confirmation question or skipped entirely — note that decision to the user and move on.

**Synthesize a refined intent paragraph** from the raw intent plus the answers, and show it back to the user in one line: _"Drafting against this intent — stop me if it's wrong: …"_. This refined paragraph is what every draft and critique in later phases will receive, so it must be self-contained (don't rely on the interview answers being visible downstream).

### 3. Resolve your slug, allocate the sprint id, reserve it in the ledger

```bash
LEDGER=.claude/skills/sprint-planner/scripts/ledger.py
SLUG=$(python3 $LEDGER whoami)                       # e.g. wayne-crosby
SID=$(python3 $LEDGER add "<short title>")           # mints + prints SPRINT-<slug>-YYYYMMDD-HHmm
```

`add` mints the id (local-clock minute) and prints it — capture that, don't hand-build it. Use a short title derived from the intent (≤60 chars). Allocation is per-user and reads no shared counter, so two developers (or two worktrees) planning at the same time can't collide.

Resolve the per-user paths once so later phases substitute literal strings (headless agents can't expand `<slug>`):

```bash
DRAFTS=docs/sprints/$SLUG/drafts        # where the drafts/critiques go
PLAN=docs/sprints/$SLUG/$SID.md         # where the merged plan goes (== ledger.py paths $SID)
mkdir -p "$DRAFTS"
```

If the sprint is grounded in a downloaded research corpus, obey the split in
`docs/adr/research-corpus-storage.md`: bodies stay at `~/research/<corpus>/`, the index is committed
under `docs/research-index/<corpus>/`, and briefs cite **source URLs**, never a `~/research/...` path
alone. If a drafter has no corpus locally, `/download-research <corpus>` restores it from the
committed URL list. Pass `--include-directories "$HOME/research"` to gemini, or its `read_file`
refuses the path while GrepTool sometimes answers anyway, which half-fails in a way that is easy to
miss.

### 4. Generate three independent drafts — in parallel

Run all three CLI calls **in the same turn** (parallel Bash tool calls). Each agent writes directly to its own draft file. Hand each agent the same intent and the same instructions about structure.

The YOLO / non-interactive invocations — these have been verified, don't second-guess them:

- **codex**: `codex exec "<prompt>" < /dev/null` — close stdin. In the Claude Code Bash tool, a bare `codex exec` prints `Reading additional input from stdin...` and then waits for the open pipe to close, which never occurs. It needs OpenAI auth. Sourcing `OPENAI_API_KEY` alone is NOT enough (codex returns 401 "Missing bearer"); do a one-time API-key login that stores creds in `~/.codex/auth.json`: `set -a; source .claude/skills/sprint-planner/.env.local; set +a; printenv OPENAI_API_KEY | codex login --with-api-key`. After that `codex exec "..."` works without sourcing. (Or `codex login` for interactive ChatGPT auth.) The key lives in `.claude/skills/sprint-planner/.env.local` (gitignored).
- **gemini**: `gemini -y --skip-trust -p "<prompt>"` — requires `GEMINI_API_KEY` in env (`-y` skips OAuth). **If the sprint reads a research corpus, add `--include-directories "$HOME/research"`.** Gemini refuses any path outside its workspace, and that flag is the portable fix; do not rely on a personal `context.includeDirectories` entry in `~/.gemini/settings.json`, because a teammate will not have one. `--skip-trust` is required in newer CLI versions (≥0.53) or it aborts with "not running in a trusted directory." The key lives in `.claude/skills/sprint-planner/.env.local` (gitignored). Source it before invoking: `set -a; source .claude/skills/sprint-planner/.env.local; set +a; gemini -y --skip-trust -p "..."`. CLI exits with code 41 if the key is unset.
- **claude**: `claude -p --dangerously-skip-permissions "<prompt>"` — the flag lets the headless agent write its draft. A `-p` run cannot answer a permission prompt, and a shell alias does not supply the flag.

**Substitute the resolved `$DRAFTS` path into each prompt — never ship a literal `<slug>` or `$DRAFTS`; headless agents won't expand it and will write to a nonsense path.** Prompt each agent with:

> You are drafting sprint **{SID}**. Intent: _{intent}_.
>
> Write a sprint plan to `{DRAFTS}/{SID}-{AGENT}.md` (where AGENT is CODEX, GEMINI, or CLAUDE as appropriate for you, and `{DRAFTS}` is the literal resolved path you were given). Freestyle the structure, but every concrete piece of work must be a checkbox task `- [ ] ...`. Cover goals, scope boundaries, task list with checkboxes, sequencing, risks, and acceptance criteria. Be concrete — task names should be things someone can actually start on.

Each agent runs headless; do not wait interactively. After all three return, verify the three files exist before moving on.

### 5. Generate three cross-critiques — in parallel

Once the drafts exist, ask each agent to critique the **other two** drafts. Again, run all three in parallel in the same turn. As in step 4, substitute the literal resolved `$DRAFTS` path into every prompt.

Prompt each critiquing agent with:

> You drafted `{DRAFTS}/{SID}-{YOU}.md` for sprint **{SID}**. Read the other two drafts at `{DRAFTS}/{SID}-{OTHER_1}.md` and `{DRAFTS}/{SID}-{OTHER_2}.md`. Write a critique to `{DRAFTS}/{SID}-{YOU}-critique.md`.
>
> For each of the other two drafts: what is stronger than yours, what is weaker, what tasks are missing, what risks are underweighted, what sequencing is wrong. Be specific and cite task names. End with a short "if I were merging, I'd keep X from draft A and Y from draft B" section.

**Gemini reads the drafts with `cat`.** `drafts/` is gitignored, and Gemini's `read_file` tool refuses every gitignored path (`is ignored by configured ignore patterns`). Add this sentence to the Gemini critique prompt: _Read each draft with `cat` in a shell command, because `read_file` refuses gitignored paths._ Gemini writes into `drafts/` with no problem.

### 6. Merge with Opus

You (the Claude session running this skill) are Opus. **Do not delegate the merge to another CLI call.** Read all six files yourself — three drafts and three critiques — and write the merged final plan directly to `$PLAN` (`docs/sprints/{SLUG}/{SID}.md`).

The merge is not an average. Prefer concrete, well-sequenced tasks. When drafts disagree, use the critiques as evidence: a task that two critiques called out as missing is probably a real gap; a task that two critiques called overengineered probably is. The final doc should feel like a single coherent plan, not a stitched compilation.

Required in the final file:

- A title line and one-paragraph restatement of intent
- Goals / non-goals
- Task list with `- [ ]` checkboxes (every actionable item)
- Sequencing (phases, dependencies, or ordering)
- Risks and mitigations
- Acceptance criteria / done-ness definition

### 7. Update the ledger

```bash
python3 $LEDGER set-status {SID} planned
```

(The sprint is already `planned` from step 3; this is a no-op unless you want to jump it straight to `in-progress`. Leave at `planned` by default — the user decides when work starts.)

### 8. Report back

Tell the user: the sprint id, the final path (`docs/sprints/{SLUG}/{SID}.md`), and a one-line summary of what the merge emphasized or deprioritized vs. the individual drafts. Don't re-dump the plan in chat — the file is the artifact.

## Ledger operations (reference)

`python3 .claude/skills/sprint-planner/scripts/ledger.py` subcommands:

| Command                                               | What it does                                                                          |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `whoami`                                              | Print the resolved current-user slug (the namespace for your sprints).                |
| `add "<title>" [--id SPRINT-<slug>-YYYYMMDD-HHmm]`    | Register a new sprint as `planned`; mints + prints the id (or reuses `--id`).         |
| `paths SPRINT-<slug>-YYYYMMDD-HHmm`                   | Print the plan path, drafts dir, and ledger for an id (use instead of hand-building). |
| `list [--mine\|--user <slug>\|--all] [--status S]`    | List sprints. Default `--mine`; `--all` walks every user and adds an owner column.    |
| `get SPRINT-<slug>-YYYYMMDD-HHmm`                     | Show one sprint's fields.                                                             |
| `set-status SID {planned,in-progress,done,abandoned}` | Change status (routes to the owning user's ledger by the id's slug).                  |
| `set-title SID "new title"`                           | Rename.                                                                               |
| `remove SID`                                          | Delete the row (does not touch the .md files).                                        |

Valid statuses: `planned`, `in-progress`, `done`, `abandoned`. There is no `next-id` — ids are minted from the clock by `add` (no shared counter to race on).

## Notes and edge cases

- **Per-user namespacing.** Your sprints live under `docs/sprints/<your-slug>/` and your ids are `SPRINT-<your-slug>-…`. You only ever write your own subtree, so concurrent planners across users/worktrees never collide and the committed ledgers merge conflict-free in git.
- **Ledger and file drift.** The ledger tracks sprint _records_; the `.md` files are the plans themselves. Removing a ledger row doesn't delete files, and vice versa. "What sprints do we have?" → trust the ledger (`list`). "Read a plan" → read the file (`paths {SID}` locates it).
- **Draft failures.** If one agent's CLI call fails (rate limits, network), surface that to the user and ask whether to retry that one agent or proceed with two drafts. Don't silently drop.
- **Re-planning.** Because the id embeds the clock minute, re-running `add` mints a _new_ id rather than overwriting. To redo a plan in place, keep the existing id and overwrite its `{SID}.md` (regenerating its drafts) without touching the ledger row. To start fresh instead, allocate a new id and `set-status {old} abandoned` so the stale row doesn't linger. Ask the user which they want — don't silently orphan the old plan.
- **Intent quality matters.** A one-line intent ("make the thing better") produces three bad drafts and a bad merge. The interview phase (step 2) exists precisely to catch this — don't skip it unless the raw intent is already explicit about scope, success, and constraints.
