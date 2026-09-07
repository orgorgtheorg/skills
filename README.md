# OrgOrg Skills

Source of truth for the public half of the **Skill Store** — the skills every
OrgOrg workspace agent can be taught. (The other half is each org's own
library, published from inside OrgSpace; same folder shape, same manifest.)

A skill is a folder: `SKILL.md` tells the agent when and how to do a job, plus
optional scripts, references, assets and a bundle. Teaching is programmatic —
the app fetches the folder from this repo (pinned at the commit sha the
catalog was last synced at) and places it at `/.skills/<id>/` on the agent's
computer. A skill that ships a **bundle** (an app, schedules) also queues one
low-priority setup task for the agent; the files still land instantly.

## Layout

```
skills/<id>/
  skill.json          # manifest — see schema/skill.schema.json
  SKILL.md            # the operating contract the agent reads
  icon.png            # 512×512 (corners are rounded by the UI). Every skill should have one.
  screenshots/*.png   # store screenshots, 01.png … — what the output looks like
  scripts/ …          # optional supporting files, shipped verbatim
  bundle/app/ …       # optional pre-built app (see below)
```

## skill.json

Enforced by `scripts/sync.mjs` and `schema/skill.schema.json`:

- `skillId` equals the folder name, lowercase-hyphenated.
- `version` is a positive integer — bump it on any meaningful change. Projects
  stay on the version they learned; the store shows them the update.
- `name`, `tagline` (≤140), `who`, `how` are the store copy. `how` renders as
  "What you get".
- `shelf` is the Browse shelf: `sales`, `marketing`, `meetings`, `research`,
  `investors`, `documents`, `security`, or `anyone`.
- `connectors` lists the services the skill uses (`{id, label, required}`);
  the store shows their marks. Ids: `gmail`, `google-calendar`, `slack`,
  `linkedin`, `notion`, `github`, `hubspot`, `salesforce`, `stripe`, `zoom`,
  `superhuman`, `microsoft`, `clay`.
- `outputs` says what it hands back: `sheet`, `doc`, `pdf`, `slides`, `video`,
  `app`, `emailDrafts`.
- `runs` is `once`, `scheduled`, or `loop`.
- `bundle` (optional) declares an app (`{ "app": true }`, code under
  `bundle/app/`, no `node_modules`, no data) and/or schedules
  (`schedules: [{ key, title, freq, time, days?, monthDay?, prompt }]`).
  Teaching creates the schedules PAUSED; the agent confirms day and timezone
  with the person before enabling them. State is created per project at setup;
  a new version replaces code and keeps data.
- `changelog` is one line on what this version changed; the store shows it
  next to the Update button.
- `featured` pins the Featured slot (at most one skill).

Never put a person's or a customer's name in a skill.

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

## Icons

One house style: a flat, two-tone glyph on a rounded-square background, no
text, 512×512. The background colour follows the shelf so a shelf reads as a
set. Generate a missing one with the prompt in `scripts/icon-prompt.md`.
