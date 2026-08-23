---
name: Code Scan
description: "Run a STATIC, white-box security review of a codebase you own. You (the coordinator) hold the threat model, the batching, and severity; you fan the reading out to dozens of cheap forked agents, each investigating one batch of candidate files against a world-class-reviewer prompt, and you accept a finding ONLY when it is proven at file:line and survived a refute pass. Use when the user asks to scan, audit, or security-review a repo, branch, or diff for vulnerabilities. It never runs, exploits, or sends a packet at anything — source only."
---

# Code Scan — the coordinator's playbook (static, white-box)

You are the coordinator. You read this; the cheap forked agents do not. The whole
design is a split of labor:

- **You** hold the threat model, the repo context, which files matter, how to
  batch them, and — at the end — severity, dedup, and is-this-real. The judgment
  does not delegate.
- **The forks** each read ONE batch of files and return structured findings. They
  do not decide scope or severity. They read closely and report.

Forking a sandbox is cents, so breadth is nearly free — you can read every file in
a large repo in one run. What is NOT free is your credibility: every false finding
you report costs it. So the product is not "more findings," it is **proven
findings and almost no noise.** Hold that the whole way through.

This skill is the deepsec method — a fast pattern scan casts a wide net, then
strong agents investigate each candidate in depth — ported onto our sandbox
fanout. If the user wants a LIVE, authorized pentest that actually fires payloads,
that is the separate `pentest` skill. This one reads source and nothing else.

---

## What this is, and what it is NOT

**Is:** a read-only, static review of code the user owns. It reads files, reads
git history, and reasons like an attacker about what the code would do. Its proof
is `file:line` plus the exact snippet.

**Is NOT — never, no exceptions:**

- No running the target code, no starting its server, no proof-of-concept scripts.
- No requests against any endpoint, no packets, no live host of any kind.
- No writing to the repo under review beyond your own report output.
- No exploitation. "Here is the vulnerable line and why it is reachable" is the
  whole job. Reproducing it is the `pentest` skill's job, not this one.

Because nothing leaves the workspace and no host is touched, there is **no
authorization gate** like the pentest skill's. One light check is enough: confirm
the user owns or may audit this code, then proceed. If they point you at a repo
that plainly is not theirs, stop and ask.

---

## The core principle (internalize this)

1. **One file is one unit of work.** The scanner, the fork that investigates it,
   and the refute pass all key on a single source file. Atomic, resumable,
   dedupable — everything falls out of that.

2. **Wide net, then judge.** A cheap, free pattern scan flags _candidate_ files —
   deliberately over-inclusive, many will be false alarms. The forks then read
   each candidate closely. You never pay a model to read a file the net did not
   flag, which is what keeps a large-repo scan affordable.

3. **Coverage is finite and known — cover every candidate exactly once.** Unlike a
   live pentest, there is no unknown-size discovery here: the file list is the file
   list. Do NOT loop-until-dry. Process each candidate once, track which are done,
   and a re-run resumes on the rest.

---

## Lean into cheap forks — the worker swarm

The unlock our sandbox gives you: a fork is a disposable copy of the whole repo
that costs cents and is thrown away when its agent finishes. So you do not read a
big repo in one long agent — you fan a **swarm of forked workers**, each holding
its own copy of the tree, each draining a batch of candidate files in parallel.
This is deepsec's "fan across N worker VMs" model, native to us.

- **Why fork, not shared:** a worker installs and runs scanners (`semgrep`,
  `gitleaks`, `ripgrep`) that write caches and scratch. Forks get their own
  filesystem and never collide, and forks have the higher concurrency cap. (If a
  worker does pure read-only reasoning with no tool that writes, `sandbox:
"shared"` + read-only tools is also legal and skips the fork copy — use it when a
  batch needs no scanner scratch.)
- **Keep the pool bounded.** Do NOT spawn one fork per file. Batch files so the run
  uses a modest, steady pool (think ~10 workers in flight, each reading 15–40
  files), the way deepsec runs `--sandboxes 10 --concurrency 4`. A finished fork is
  _paused, not deleted_, and paused sandboxes bill storage — so a run that spawns
  hundreds of tiny forks leaves a mess. Fewer, fuller workers is both cheaper and
  faster.

---

## The ladder — walk it in order

```
1. Context      read the repo once → a short threat model + ingress inventory
2. Scan         pattern-match the whole tree → candidate files (free, no model)
3. Batch        group candidates into ~10–20 worker batches by area
4. Investigate  fan forked workers → each reads its batch → structured findings
5. Revalidate   refute each finding; check git history for a fix → drop the weak
6. Report       dedup, severity, write the report + findings sheet to /Apps
```

Run scan+batch yourself (or with one cheap helper), then run **Investigate** and
**Revalidate** as one `run_workflow` script (fan → refute → `report()` up). Read
the result and write the report yourself — your judgment belongs at the ends, not
inside the grinding.

---

## Phase 1 — Context (one shared, read-only agent)

Before any scanning, get the lay of the land. One `shared` read-only agent reads
the top of the tree and returns a terse threat model you inject into every later
fork: what the app is, its languages/frameworks, where untrusted input enters
(HTTP routes, webhooks, queues, file uploads, CLI args), where the sensitive sinks
are (DB, shell, file paths, outbound fetch, templating, auth). Keep it to a page.
This is deepsec's `INFO.md` — it makes every downstream reviewer sharper.

## Phase 2 — Scan (candidates, free, no model)

Cast the wide net. Run pattern matchers over the whole tree to flag candidate
files — anywhere untrusted input can reach a dangerous sink. `semgrep --config
p/owasp-top-ten --config p/secrets`, plus `gitleaks detect` / `trufflehog` over
**full git history** for committed secrets. Also grep for the raw sink shapes the
threat model named. The output is a list of `{ file, why_flagged }` — candidates,
not findings. Over-include on purpose; the forks filter.

## Phase 3 — Batch

Group the candidate files into ~10–20 batches, ideally by area (auth, API
handlers, DB layer, upload, templating, config/secrets) so each worker holds a
coherent slice and one reviewer sees a whole subsystem. Aim for 15–40 files per
batch. This batching is yours — it is where repo knowledge turns into good units.

## Phase 4 — Investigate (the expensive stage). One forked worker per batch.

Each fork reads every file in its batch and returns structured findings. Give it
the reviewer prompt below verbatim (fill in the batch and the injected threat
model). Same prompt for every fork — consistency is what lets you aggregate.

```js
agent(
  `You are a world-class security researcher reviewing code we OWN. Static review only — do NOT run, exploit, or send any request; read the source.

   Repo context (threat model):
   ${INFO}

   Investigate these candidate files closely. The pattern scanner flagged them; treat that as a starting point, not the answer — read each file for ANY security issue, especially subtle ones (auth bypass via parameter manipulation, cross-tenant IDs, race conditions, trust-boundary violations), not just the flagged pattern. Files:
   ${batchFileList}

   SEVERITY:
   - CRITICAL: RCE, full auth bypass, SQLi on sensitive data, upload→RCE, SSRF to internal services.
   - HIGH: XSS, SSRF, privilege escalation, hardcoded secrets in source, insecure deserialization, missing authz on sensitive ops.
   - MEDIUM: open redirect, weak crypto, missing rate limiting, info disclosure, IDOR, race conditions, logic bugs in auth/permission checks.

   FALSE-POSITIVE GUARD — before you flag anything, check for a mitigation and DROP it if fully mitigated:
   - Is the input parameterized / escaped / sanitized before the sink?
   - Is there a guard that WRAPS this handler directly (Express middleware, Fastify hook, NestJS guard, Spring filter, Rails before_action, Django decorator, FastAPI Depends)? Edge/proxy/CDN/WAF rules that run BEFORE the handler do NOT count — too easy to bypass.
   - Is the pattern only ever used with trusted/internal data, not user input?
   Report ONLY genuine, reachable, exploitable issues.

   AUTH-BYPASS PATTERNS to look for specifically: parameter pollution (?id=x&id=y), encoded/double-encoded/null-byte paths, route-param injection to reach other users' data, OAuth state/redirect_uri tampering, JWT missing algorithm pinning or test tokens reachable in prod, blindly-trusted x-* / X-Forwarded-* headers, cross-tenant access (user-supplied teamId/userId used in queries instead of the authenticated identity), auth that proves "logged in" but not "owns this resource", negated permission checks.

   Skip gitignored, generated, vendored, or non-production files.

   Return ONLY: { findings: [{ slug, title, severity, file, line, snippet, reasoning }] }. slug is a short category like "sql-injection" or "auth-bypass". Empty findings array is a valid, common answer.`,
  {
    tools: ["read", "grep", "bash"],
    sandbox: "fork",
    purpose: "review auth + API handlers",
    schema: {
      type: "object",
      properties: {
        findings: {
          type: "array",
          items: {
            type: "object",
            properties: {
              slug: { type: "string" },
              title: { type: "string" },
              severity: {
                type: "string",
                enum: ["CRITICAL", "HIGH", "MEDIUM"],
              },
              file: { type: "string" },
              line: { type: "number" },
              snippet: { type: "string" },
              reasoning: { type: "string" },
            },
            required: [
              "slug",
              "title",
              "severity",
              "file",
              "line",
              "reasoning",
            ],
          },
        },
      },
      required: ["findings"],
    },
  },
);
```

Keep every schema inside the validator's supported subset: `type`, `properties`,
`required`, `items`, `enum`, `minItems`/`maxItems`, `minimum`/`maximum`,
`additionalProperties: false`, `description`. A schema that uses `pattern`,
`format`, `minLength`, `anyOf`, `$ref`, etc. cannot be satisfied — the worker can
never finish and only dies at its deadline. Stick to the subset above.

## Phase 5 — Revalidate (refute + git history). One `llm()` per finding.

This is the stage that separates a scanner from a review — deepsec measures it
cutting false positives by 50%+. For every candidate finding, one cheap `llm()`
call told to DISPROVE it and to check whether git history already fixed it:

```js
llm(
  `A reviewer flagged this as a vulnerability. Try to REFUTE it. Default to refuted:true if the evidence is weak, ambiguous, environment-specific, or looks mitigated.
   Also decide if git history shows it was already fixed: run \`git log -p -S '<the vulnerable token>' -- <file>\` and look for a later commit that added a guard/escape/parameterization on this line.
   Finding: ${JSON.stringify(finding)}
   A finding SURVIVES only if the vulnerable line is real, reachable with attacker-controlled input, and NOT mitigated or already fixed.
   Return: { verdict, reasoning }  // verdict one of: true-positive, false-positive, fixed, uncertain`,
  {
    schema: {
      type: "object",
      properties: {
        verdict: {
          type: "string",
          enum: ["true-positive", "false-positive", "fixed", "uncertain"],
        },
        reasoning: { type: "string" },
      },
      required: ["verdict", "reasoning"],
    },
  },
);
```

Keep only `true-positive` (and surface `uncertain` separately as "worth a human
look", never as a confirmed finding). Drop `false-positive` and `fixed`.

## Phase 6 — Report (you write this)

Dedup survivors by `slug + title + file` (the same issue found by two workers is
one finding). Then, for each:

- **Title + severity** — your judgment, honest. Most real findings are MEDIUM; do
  not inflate.
- **Where** — `file:line` and the exact snippet.
- **Why it is real** — the attacker path in one or two sentences, from your
  reasoning across the codebase, not the fork's raw text.
- **Fix** — one concrete remediation.

Deliver a report doc plus a findings sheet in the workspace (`/Apps`). This is an
internal report to the code owner — do **not** submit it anywhere external.

---

## Coverage & resume

The candidate list is finite, so completeness is checkable: every candidate file
belongs to exactly one batch, and every batch was investigated. `log()` any batch
you skipped (e.g. a worker that errored) so nothing reads as covered that was not.
If a run is interrupted, resume by re-batching only the candidates with no finding
record yet — reuse a stopped workflow's finished workers with `resumeFrom` so you
do not pay twice for the same batch. Nothing here loops-until-dry; it converges
when the candidate list is exhausted.

---

## Runtime & scale notes

- **Bounded fork pool.** A workflow runs at most ~10 forks at once (and ~200 over
  its life). Size batches so the whole run is ~10–20 workers, not one per file.
  Finished forks are paused (not deleted) and bill storage, so fewer, fuller
  workers is cheaper — and faster, since a wave stalls on its slowest worker.
- **Structured output is mandatory.** Always pass a `schema` (within the supported
  subset above) so you can machine-read, dedup, and aggregate. A worker that
  returns prose is a worker you cannot merge.
- **Cost lives in the model, not the sandbox.** A forked worker inherits your model
  — there is no cheap-tier fork today — so "cheap forks" means cheap _sandboxes_,
  not cheap tokens. The lever that keeps a large scan affordable is the free
  pattern pre-filter: you only ever pay a model to read candidate files, never the
  whole tree. That is deepsec's economics, and it is why Phase 2 must cast a wide
  but not infinite net.
- **Golden image.** Workers need only a light static kit: `semgrep`, `gitleaks` (or
  `trufflehog`), and `ripgrep`. No browser, no network tooling, no exploit
  frameworks — this is the pentest image minus the offensive half. If a tool is
  missing a worker wastes minutes installing it, so treat the kit as a
  prerequisite.
- **Diff mode.** For a PR gate, scope Phase 2 to the files a diff touched
  (`git diff --name-only origin/main`), batch those, and report only net-new
  findings. Same pipeline, a fraction of the cost.

---

## The whole thing in one paragraph

Confirm the user owns the code. Read the repo once to build a one-page threat
model. Run a free pattern scan over the whole tree to flag candidate files — cast
wide, over-include. Batch the candidates by area into ~10–20 slices, and fan a
forked worker at each: it reads its files closely against a world-class-reviewer
prompt, static only, and returns structured findings. Refute every finding with a
cheap pass that also checks git history for a fix, and drop everything that does
not survive. Dedup what is left, set honest severities, and write a report with
`file:line`, a snippet, the attacker path, and a fix for each — delivered to the
owner and no one else. You hold the threat model, the batching, and the judgment;
the forks only read.
