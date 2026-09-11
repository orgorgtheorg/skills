# OrgOrg Skills

Source of truth for the public tier of the **Skill Store** — the skills any
OrgSpace agent can be taught. (An org's own skills live in the app, in its
library; agents publish those with the `orgspace skill` CLI. Same manifest.)

A skill is a job an agent can do: a folder whose `SKILL.md` tells the agent
when and how to do it, plus optional scripts, references, assets, and — since
v2 — an optional **bundle**: a pre-built artifact app and/or schedules.
Teaching is programmatic: the app fetches the folder from this repo (pinned at
the commit sha the catalog was last synced at) and places it at
`/.skills/<id>/` on the agent's computer. A skill with a bundle also queues
one low-priority setup task for the agent, which copies the app in and
proposes the schedules, paused. An agent stays on the version it learned
until a person teaches it a newer one from the store — nothing auto-updates.

## Layout

```
skills/<id>/
  skill.json        # manifest v2 — see schema/skill.schema.json
  SKILL.md          # the operating contract the agent reads
  icon.png          # required, 512×512, flat two-tone (corners rounded by the UI)
  screenshots/*.png # optional store screenshots, shown on the skill page
  scripts/ …        # optional supporting files, shipped verbatim
  bundle/app/ …     # optional pre-built artifact app (declared in skill.json)
```

`skill.json` rules (enforced by `scripts/sync.mjs --check`):

- `skillId` equals the folder name, lowercase-hyphenated.
- `version` is a positive integer — bump it on any meaningful change, and put
  one line in `changelog` saying what changed (the store shows it before an
  update).
- `name`, `tagline` (≤140 chars), `who`, `how` are the card and page copy.
  `how` is shown as "What you get": mechanism and outcome, two to four
  sentences.
- `shelf` is one of `sales` / `marketing` / `meetings` / `research` /
  `investors` / `documents` / `security` / `anyone`. One shelf per skill.
- `tags` are free words for search.
- `outputs` says what comes back: `sheet`, `doc`, `pdf`, `video`, `app`,
  `emailDrafts`, `slides`, `report`.
- `runs` is `once`, `scheduled`, or `loop`.
- `needs` carries `desktopSignIn` (sites to sign in to on the shared desktop),
  `forksWorkers`, and `estMinutes`. Use `{}` for none.
- `connectors` lists the services it talks to (`{id, label, required}`). The
  store draws the real logo for known ids — see the schema for the list.
- `examples` links real outputs from a demo run (`{title, kind, url}`); `[]`
  until there are some.
- `bundle` (optional) declares `app: { path, name? }`, `apps: [{ path, name }]` for several, and/or `schedules: [...]`.
  Schedules are created paused; never rely on one starting by itself.
- `icon.png` is required. Flat, two-tone, one subject, no text.

Write SKILL.md for an agent that does not know the org: the person's
decisions become `ask_question` steps, org facts become parameters, and no
person's or company's name ever appears in the folder.

A template with every field filled in is in `docs/template/`.

## Publishing

Push to `main`. The **Sync catalog** Action validates every manifest and
mirrors the catalog (manifests + commit sha + artwork URLs) into the dev and
prod Convex deployments via `agentInfra/skillCatalogSync:syncCatalog`.
Pushing is the publish step: teaching downloads
`codeload.github.com/orgorgtheorg/skills/tar.gz/<sha>`, so the sha must exist
on GitHub.

Validate locally with:

```
node scripts/sync.mjs --check
```
