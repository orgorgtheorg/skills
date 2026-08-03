// Validate every skills/<id>/skill.json and mirror the catalog into a Convex
// deployment (agentInfra/skillCatalogSync:syncCatalog). Dependency-free on
// purpose: validation is hand-rolled against the same rules as
// schema/skill.schema.json and the sync is a plain fetch, so CI needs nothing
// beyond node.
//
//   node scripts/sync.mjs --check               validate only
//   CONVEX_DEPLOY_KEY=… node scripts/sync.mjs   validate + sync
//
// Repo + sha come from GitHub Actions env (GITHUB_REPOSITORY / GITHUB_SHA)
// with git fallbacks for local runs.
import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const CATEGORIES = new Set(["growth", "operations", "build", "general"]);
const SKILLS_DIR = "skills";

function fail(msg) {
  console.error(`✖ ${msg}`);
  process.exitCode = 1;
}

function validate(id, m) {
  const ctx = `skills/${id}/skill.json`;
  if (m.skillId !== id)
    fail(`${ctx}: skillId "${m.skillId}" must equal folder name "${id}"`);
  if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(String(m.skillId ?? "")))
    fail(`${ctx}: bad skillId`);
  if (!Number.isInteger(m.version) || m.version < 1)
    fail(`${ctx}: version must be a positive integer`);
  for (const key of ["name", "tagline", "who", "how"]) {
    if (typeof m[key] !== "string" || m[key].length === 0)
      fail(`${ctx}: missing ${key}`);
  }
  if (m.tagline && m.tagline.length > 140) fail(`${ctx}: tagline > 140 chars`);
  if (!CATEGORIES.has(m.category))
    fail(`${ctx}: category must be one of ${[...CATEGORIES].join("/")}`);
  if (m.accent !== undefined && typeof m.accent !== "string")
    fail(`${ctx}: accent must be a string`);
  if (!Array.isArray(m.connectors)) fail(`${ctx}: connectors must be an array`);
  for (const c of m.connectors ?? []) {
    if (
      typeof c.id !== "string" ||
      typeof c.label !== "string" ||
      typeof c.required !== "boolean"
    ) {
      fail(`${ctx}: connector entries need {id, label, required}`);
    }
  }
  const allowed = new Set([
    "skillId",
    "version",
    "name",
    "tagline",
    "who",
    "how",
    "category",
    "accent",
    "connectors",
  ]);
  for (const key of Object.keys(m)) {
    if (!allowed.has(key)) fail(`${ctx}: unknown key "${key}"`);
  }
}

const ids = readdirSync(SKILLS_DIR, { withFileTypes: true })
  .filter((e) => e.isDirectory())
  .map((e) => e.name)
  .sort();

const skills = [];
for (const id of ids) {
  const manifestPath = join(SKILLS_DIR, id, "skill.json");
  if (!existsSync(manifestPath)) {
    fail(`skills/${id}/ has no skill.json`);
    continue;
  }
  let manifest;
  try {
    manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  } catch (err) {
    fail(`${manifestPath}: invalid JSON — ${err.message}`);
    continue;
  }
  validate(id, manifest);
  if (!existsSync(join(SKILLS_DIR, id, "SKILL.md"))) {
    fail(`skills/${id}/ has no SKILL.md — a skill IS its SKILL.md`);
  }
  // Artwork is convention, not manifest fields: icon.png + screenshots/*.
  // Relative paths here; the sync phase turns them into raw.githubusercontent
  // URLs pinned at the synced commit.
  const iconPath = existsSync(join(SKILLS_DIR, id, "icon.png"))
    ? `skills/${id}/icon.png`
    : null;
  const shotsDir = join(SKILLS_DIR, id, "screenshots");
  const screenshotPaths = existsSync(shotsDir)
    ? readdirSync(shotsDir)
        .filter((f) => /\.(png|jpe?g|webp)$/i.test(f))
        .sort()
        .map((f) => `skills/${id}/screenshots/${f}`)
    : [];
  skills.push({ ...manifest, iconPath, screenshotPaths });
}

if (process.exitCode) {
  console.error("Validation failed — not syncing.");
  process.exit(1);
}
console.log(
  `✔ ${skills.length} manifests valid (${skills.filter((s) => s.iconPath).length} with icons)`,
);

if (process.argv.includes("--check")) {
  process.exit(0);
}

if (!process.env.CONVEX_DEPLOY_KEY) {
  console.log("CONVEX_DEPLOY_KEY not set — skipping sync.");
  process.exit(0);
}

const git = (...args) => execFileSync("git", args, { encoding: "utf8" }).trim();
const repo =
  process.env.GITHUB_REPOSITORY ??
  git("remote", "get-url", "origin")
    .replace(/^.*github\.com[:/]/, "")
    .replace(/\.git$/, "");
const commitSha = process.env.GITHUB_SHA ?? git("rev-parse", "HEAD");

const raw = (path) =>
  `https://raw.githubusercontent.com/${repo}/${commitSha}/${path}`;
const payloadSkills = skills.map(({ iconPath, screenshotPaths, ...skill }) => ({
  ...skill,
  ...(iconPath ? { iconUrl: raw(iconPath) } : {}),
  ...(screenshotPaths.length > 0
    ? { screenshotUrls: screenshotPaths.map(raw) }
    : {}),
}));
// Call the deployment's function HTTP API directly rather than shelling out to
// `npx convex run` — the CLI insists on being run from a Convex app root (a
// package.json with convex as a dependency), which this repo deliberately
// isn't. The deploy key doubles as the admin bearer token and names its own
// deployment: "dev:dusty-ferret-895|<secret>".
const deployKey = process.env.CONVEX_DEPLOY_KEY;
const deploymentName = deployKey.split("|")[0].split(":").pop();
const url = process.env.CONVEX_URL ?? `https://${deploymentName}.convex.cloud`;

console.log(
  `Syncing ${skills.length} skills @ ${commitSha.slice(0, 10)} (${repo}) → ${deploymentName}…`,
);
const res = await fetch(
  `${url}/api/run/agentInfra/skillCatalogSync/syncCatalog`,
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Convex ${deployKey}`,
    },
    body: JSON.stringify({
      args: { repo, commitSha, skills: payloadSkills },
      format: "json",
    }),
  },
);
const body = await res.json().catch(() => null);
if (!res.ok || body?.status !== "success") {
  fail(
    `sync failed (HTTP ${res.status}): ${body ? JSON.stringify(body) : await res.text()}`,
  );
  process.exit(1);
}
console.log(
  `✔ synced — upserted ${body.value.upserted}, deleted ${body.value.deleted}`,
);
