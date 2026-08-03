# OrgOrg Skills

Source of truth for the **Skill Store** — the first-party skills an OrgOrg
workspace agent can be taught.

A skill is pure knowledge: a folder whose `SKILL.md` tells the agent when and
how to do a job, plus optional scripts, references, and assets. Teaching is
programmatic — the app fetches the folder from this repo (pinned at the commit
sha the catalog was last synced at) and places it at `/.skills/<id>/` on the
agent's computer. There are no install steps and nothing to provision; if an
idea needs provisioning or a backing app, it belongs to a future _apps_
concept, not here.

## Layout

```
skills/<id>/
  skill.json        # manifest — see schema/skill.schema.json
  SKILL.md          # the operating contract the agent reads
  icon.png          # optional, 512×512 (corners are rounded by the UI)
  screenshots/*.png # optional store screenshots
  scripts/ …        # optional supporting files, shipped verbatim
```

`skill.json` rules (enforced by `scripts/sync.mjs`):

- `skillId` equals the folder name, lowercase-hyphenated.
- `version` is a positive integer — bump it on any meaningful change.
- `name`, `tagline` (≤140 chars), `who`, `how` are the store card copy.
- `category` is one of `growth` / `operations` / `build` / `general`.
- `connectors` lists integrations the skill uses (`{id, label, required}`).

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
