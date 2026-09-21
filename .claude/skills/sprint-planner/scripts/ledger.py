#!/usr/bin/env python3
"""Sprint ledger CRUD.

Sprints are namespaced **per git user** so multiple developers (and multiple
git worktrees) can run sprints concurrently without colliding. Each user owns a
subtree ``docs/sprints/<slug>/`` containing their own ``ledger.yaml`` and their
final ``SPRINT-<slug>-YYYYMMDD-HHmm.md`` plans. The slug is baked into the
canonical sprint id, so a bare id is never ambiguous in a code comment or commit.

Statuses: planned | in-progress | done | abandoned.

The on-disk format is a deliberately narrow subset of YAML (a top-level
``sprints:`` list of flat string-valued records). We parse and emit it by hand
so this script has zero third-party dependencies (stdlib only).
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

STATUSES = ["planned", "in-progress", "done", "abandoned"]
# Canonical id: SPRINT-<slug>-YYYYMMDD-HHmm. The slug is non-greedy so a slug
# that itself contains digits (e.g. "user2") can't swallow the date group.
SPRINT_RE = re.compile(r"^SPRINT-(?P<slug>[a-z0-9-]+?)-(?P<date>\d{8})-(?P<time>\d{4})$")
FIELDS = ("id", "owner", "title", "status", "executor", "created", "updated")
# Examples only — set-executor accepts any model name (the Claude session's
# model varies: fable, opus, sonnet, ...).
EXECUTORS = ["fable", "opus", "gpt-5.5", "gemini"]


def _git(*args: str) -> str | None:
    """Run a git command and return stripped stdout, or None on any failure.

    Used for repo-root and user-identity resolution. Treats a missing git
    binary, a non-zero exit, or empty output as "value absent" so callers can
    fall through to the next option.
    """
    try:
        out = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=False
        )
    except (FileNotFoundError, OSError):
        return None
    if out.returncode != 0:
        return None
    value = out.stdout.strip()
    return value or None


def slugify(s: str) -> str:
    """lowercase, non-alphanumerics -> '-', strip leading/trailing '-'."""
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def current_user_slug() -> str:
    """Resolve the current user's slug.

    Fallback chain: git config sprint.slug -> git user.name -> local-part of
    git user.email -> $USER/$USERNAME -> the literal "unknown". Each candidate
    is slugified, and an empty slug falls through to the next candidate.

    ``sprint.slug`` is a per-clone override (``git config sprint.slug <slug>``)
    for a user whose ledger directory does not match their current
    ``user.name``; it never changes commit authorship.
    """
    override = _git("config", "sprint.slug")
    if override and slugify(override):
        return slugify(override)
    name = _git("config", "user.name")
    if name and slugify(name):
        return slugify(name)
    email = _git("config", "user.email")
    if email and "@" in email and slugify(email.split("@", 1)[0]):
        return slugify(email.split("@", 1)[0])
    for env_var in ("USER", "USERNAME"):
        val = os.environ.get(env_var)
        if val and slugify(val):
            return slugify(val)
    return "unknown"


def project_root() -> Path:
    """The repository root, correct even inside a git worktree.

    Prefer ``git rev-parse --show-toplevel`` (cwd-independent, resolves each
    worktree to its own root). Fall back to walking up from this script's
    location for non-git contexts (e.g. a source tarball, a CI checkout with no
    ``.git``). The script lives at
    ``<root>/.claude/skills/sprint-planner/scripts/ledger.py`` — four parents up.
    """
    top = _git("rev-parse", "--show-toplevel")
    if top:
        return Path(top)
    return Path(__file__).resolve().parents[4]


def user_sprints_dir(slug: str) -> Path:
    return project_root() / "docs" / "sprints" / slug


def ledger_path(slug: str | None = None) -> Path:
    if slug is None:
        slug = current_user_slug()
    return user_sprints_dir(slug) / "ledger.yaml"


def new_id(slug: str | None = None) -> str:
    """Mint a fresh id from the local-clock minute: SPRINT-<slug>-YYYYMMDD-HHmm.

    Local time (not UTC) so the id matches the developer's wall clock. No shared
    state is read, so two worktrees can never race on id allocation.
    """
    if slug is None:
        slug = current_user_slug()
    return f"SPRINT-{slug}-{dt.datetime.now():%Y%m%d-%H%M}"


def slug_from_id(sprint_id: str) -> str | None:
    m = SPRINT_RE.match(sprint_id or "")
    return m.group("slug") if m else None


def _yaml_escape(value: str) -> str:
    # Quote anything that could confuse the narrow parser; otherwise leave bare.
    if value == "" or any(c in value for c in ":#\"'\n") or value.strip() != value:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def _yaml_unescape(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        inner = value[1:-1]
        if value[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner
    return value


def _parse_ledger(text: str) -> list[dict]:
    sprints: list[dict] = []
    current: dict | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line == "sprints:" or line == "sprints: []":
            continue
        stripped = line.lstrip()
        if stripped.startswith("- "):
            if current is not None:
                sprints.append(current)
            current = {}
            stripped = stripped[2:]
            if ":" in stripped:
                k, _, v = stripped.partition(":")
                current[k.strip()] = _yaml_unescape(v)
            continue
        if current is None:
            continue
        if ":" in stripped:
            k, _, v = stripped.partition(":")
            current[k.strip()] = _yaml_unescape(v)
    if current is not None:
        sprints.append(current)
    return sprints


def load(slug: str | None = None) -> dict:
    """Load one user's ledger (the current user's by default)."""
    p = ledger_path(slug)
    if not p.exists():
        return {"sprints": []}
    return {"sprints": _parse_ledger(p.read_text())}


def load_all() -> dict:
    """Merge every user's ledger by walking docs/sprints/*/ledger.yaml.

    Each row carries an ``owner`` field; rows missing it are stamped with the
    directory name so cross-user listings are always attributable.
    """
    sprints_root = project_root() / "docs" / "sprints"
    rows: list[dict] = []
    if not sprints_root.exists():
        return {"sprints": rows}
    for ledger in sorted(sprints_root.glob("*/ledger.yaml")):
        owner = ledger.parent.name
        for s in _parse_ledger(ledger.read_text()):
            s.setdefault("owner", owner)
            rows.append(s)
    return {"sprints": rows}


def save(data: dict, slug: str | None = None) -> None:
    p = ledger_path(slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = ["sprints:"]
    if not data["sprints"]:
        lines = ["sprints: []"]
    else:
        for s in data["sprints"]:
            first = True
            for k in FIELDS:
                if k not in s:
                    continue
                prefix = "  - " if first else "    "
                lines.append(f"{prefix}{k}: {_yaml_escape(str(s[k]))}")
                first = False
    p.write_text("\n".join(lines) + "\n")


def now() -> str:
    """UTC timestamp for the audit fields (created/updated). The *id* uses local
    time via ``new_id``; these audit stamps stay UTC for cross-machine ordering."""
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def find(data: dict, sprint_id: str) -> dict | None:
    for s in data["sprints"]:
        if s.get("id") == sprint_id:
            return s
    return None


def _owner_slug_for(sprint_id: str) -> str:
    """The slug whose ledger owns this id. Falls back to the current user when
    the id isn't a recognized SPRINT-<slug>-... form (callers also validate)."""
    return slug_from_id(sprint_id) or current_user_slug()


def cmd_add(args) -> int:
    slug = current_user_slug()
    if args.id:
        if not SPRINT_RE.match(args.id):
            sys.stderr.write(
                f"--id {args.id!r} is not a valid SPRINT-<slug>-YYYYMMDD-HHmm id\n"
            )
            return 1
        sid = args.id
        owner = slug_from_id(sid)
    else:
        sid = new_id(slug)
        owner = slug
    data = load(owner)
    if find(data, sid):
        sys.stderr.write(f"{sid} already exists\n")
        return 1
    data["sprints"].append({
        "id": sid,
        "owner": owner,
        "title": args.title,
        "status": "planned",
        "created": now(),
        "updated": now(),
    })
    save(data, owner)
    print(sid)
    return 0


def cmd_list(args) -> int:
    if args.all:
        data = load_all()
        show_owner = True
    elif args.user:
        data = load(args.user)
        show_owner = True
    else:
        data = load(current_user_slug())
        show_owner = False
    rows = data["sprints"]
    if args.status:
        rows = [s for s in rows if s.get("status") == args.status]
    if not rows:
        return 0
    id_w = max(len(s.get("id", "")) for s in rows)
    if show_owner:
        owner_w = max(len(s.get("owner", "")) for s in rows)
        for s in rows:
            print(
                f"{s.get('id',''):<{id_w}}  {s.get('owner',''):<{owner_w}}  "
                f"{s.get('status',''):<12}  {s.get('title','')}"
            )
    else:
        for s in rows:
            print(f"{s.get('id',''):<{id_w}}  {s.get('status',''):<12}  {s.get('title','')}")
    return 0


def cmd_get(args) -> int:
    data = load(_owner_slug_for(args.id))
    s = find(data, args.id)
    if not s:
        sys.stderr.write(f"{args.id} not found\n")
        return 1
    for k in FIELDS:
        if k in s:
            print(f"{k}: {s[k]}")
    return 0


def cmd_paths(args) -> int:
    slug = slug_from_id(args.id)
    if not slug:
        sys.stderr.write(
            f"{args.id!r} is not a valid SPRINT-<slug>-YYYYMMDD-HHmm id\n"
        )
        return 1
    d = user_sprints_dir(slug)
    print(f"plan: {d / (args.id + '.md')}")
    print(f"drafts: {d / 'drafts'}")
    print(f"ledger: {d / 'ledger.yaml'}")
    return 0


def cmd_whoami(_args) -> int:
    # The slug is the contract (stdout); the derivation source is a debugging
    # aid (stderr) so callers can capture just the slug.
    name = _git("config", "user.name")
    email = _git("config", "user.email")
    slug = current_user_slug()
    if name and slugify(name):
        source = "git user.name"
    elif email and "@" in email and slugify(email.split("@", 1)[0]):
        source = "git user.email"
    elif any(os.environ.get(v) for v in ("USER", "USERNAME")):
        source = "env"
    else:
        source = "fallback"
    sys.stderr.write(f"(source: {source})\n")
    print(slug)
    return 0


def cmd_set_status(args) -> int:
    slug = _owner_slug_for(args.id)
    data = load(slug)
    s = find(data, args.id)
    if not s:
        sys.stderr.write(f"{args.id} not found\n")
        return 1
    s["status"] = args.status
    s["updated"] = now()
    save(data, slug)
    return 0


def cmd_set_executor(args) -> int:
    slug = _owner_slug_for(args.id)
    data = load(slug)
    s = find(data, args.id)
    if not s:
        sys.stderr.write(f"{args.id} not found\n")
        return 1
    if args.executor == "":
        s.pop("executor", None)
    else:
        s["executor"] = args.executor
    s["updated"] = now()
    save(data, slug)
    return 0


def cmd_set_title(args) -> int:
    slug = _owner_slug_for(args.id)
    data = load(slug)
    s = find(data, args.id)
    if not s:
        sys.stderr.write(f"{args.id} not found\n")
        return 1
    s["title"] = args.title
    s["updated"] = now()
    save(data, slug)
    return 0


def cmd_remove(args) -> int:
    slug = _owner_slug_for(args.id)
    data = load(slug)
    before = len(data["sprints"])
    data["sprints"] = [s for s in data["sprints"] if s.get("id") != args.id]
    if len(data["sprints"]) == before:
        sys.stderr.write(f"{args.id} not found\n")
        return 1
    save(data, slug)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="ledger")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="register a new sprint (status=planned); mints the id")
    a.add_argument("title")
    a.add_argument("--id", help="use this exact id instead of minting one (migration/replan)")
    a.set_defaults(func=cmd_add)

    l = sub.add_parser("list", help="list sprints (default: yours)")
    scope = l.add_mutually_exclusive_group()
    scope.add_argument("--mine", action="store_true", help="only your sprints (default)")
    scope.add_argument("--user", help="only this user's sprints")
    scope.add_argument("--all", action="store_true", help="every user's sprints (adds owner column)")
    l.add_argument("--status", choices=STATUSES)
    l.set_defaults(func=cmd_list)

    g = sub.add_parser("get")
    g.add_argument("id")
    g.set_defaults(func=cmd_get)

    pa = sub.add_parser("paths", help="print plan/drafts/ledger paths for an id")
    pa.add_argument("id")
    pa.set_defaults(func=cmd_paths)

    w = sub.add_parser("whoami", help="print the resolved current-user slug")
    w.set_defaults(func=cmd_whoami)

    s = sub.add_parser("set-status")
    s.add_argument("id")
    s.add_argument("status", choices=STATUSES)
    s.set_defaults(func=cmd_set_status)

    e = sub.add_parser("set-executor", help="record which model is implementing the sprint")
    e.add_argument("id")
    e.add_argument("executor", help=f"the implementing model, e.g. {EXECUTORS}; or '' to clear")
    e.set_defaults(func=cmd_set_executor)

    t = sub.add_parser("set-title")
    t.add_argument("id")
    t.add_argument("title")
    t.set_defaults(func=cmd_set_title)

    r = sub.add_parser("remove")
    r.add_argument("id")
    r.set_defaults(func=cmd_remove)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
