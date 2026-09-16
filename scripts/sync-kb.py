#!/usr/bin/env python3
"""sync-kb — project the repository's knowledge into the Obsidian vault ``kb-sherpa/`` (one way, stdlib only).

The vault is a **projection, never a source**: every note is a copy of a tracked file with front matter injected,
laid out under the file's repository path so relative links keep working. Files that no longer exist in the
repository are removed from the vault; a full run is a mirror. ``kb-sherpa/`` is ignored by git.

What is synced (``SOURCES``): README, CLAUDE.md, LICENSE, ``docs/**/*.md``, the harness under ``.claude/``
(agents, skills, commands, docs), the JSON schemas and the plan goldens as code notes (``x.json.md`` with a fenced
block), plus a generated ``Home.md`` index.

Usage:
  python3 scripts/sync-kb.py            # full sync → kb-sherpa/
  python3 scripts/sync-kb.py --check    # exit 1 when the vault is out of date (nothing written)
  python3 scripts/sync-kb.py --vault P  # another vault directory

Front matter per note: ``title``, ``type`` (readme | rules | doc | adr | command | concept | reference | agent |
skill | claude-command | owner-doc | schema | golden | license), ``source`` (repository path), ``synced`` (last
commit date of the source on HEAD, or ``uncommitted``), ``tags``.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "kb-sherpa"
SOURCES = (
    "README.md",
    "CLAUDE.md",
    "LICENSE",
    "docs/**/*.md",
    ".claude/agents/*.md",
    ".claude/skills/*/SKILL.md",
    ".claude/commands/*.md",
    ".claude/docs/**/*.md",
    "src/sherpa/schemas/*.json",
    "tests/goldens/*",
)
_FRONT = re.compile(r"\A---[ \t]*\n.*?\n---[ \t]*\n", re.S)


def note_type(rel: str) -> str:
    if rel == "README.md":
        return "readme"
    if rel == "CLAUDE.md":
        return "rules"
    if rel == "LICENSE":
        return "license"
    if rel.startswith("docs/adr/"):
        return "adr"
    if rel.startswith("docs/commands/"):
        return "command"
    if rel.startswith("docs/concepts/"):
        return "concept"
    if rel.startswith("docs/reference/"):
        return "reference"
    if rel.startswith("docs/"):
        return "doc"
    if rel.startswith(".claude/agents/"):
        return "agent"
    if rel.startswith(".claude/skills/"):
        return "skill"
    if rel.startswith(".claude/commands/"):
        return "claude-command"
    if rel.startswith(".claude/docs/"):
        return "owner-doc"
    if rel.startswith("src/sherpa/schemas/"):
        return "schema"
    if rel.startswith("tests/goldens/"):
        return "golden"
    return "file"


def sources() -> list[Path]:
    out: set[Path] = set()
    for pattern in SOURCES:
        out.update(p for p in ROOT.glob(pattern) if p.is_file())
    return sorted(out)


def last_commit_dates() -> dict[str, str]:
    """rel path → ISO date of the last commit touching it (one git call)."""
    try:
        log = subprocess.run(
            ["git", "-C", str(ROOT), "log", "--format=%x00%cs", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, OSError):
        return {}
    dates: dict[str, str] = {}
    current = ""
    for line in log.splitlines():
        if line.startswith("\x00"):
            current = line[1:]
        elif line and line not in dates:
            dates[line] = current
    return dates


def title_of(rel: str, text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip().replace('"', "'")
    return Path(rel).name


def render(rel: str, text: str, synced: str) -> str:
    kind = note_type(rel)
    tags = ["sherpa", kind]
    if rel.startswith("docs/adr/") and rel != "docs/adr/README.md":
        tags.append("decision")
    is_md = rel.endswith(".md")
    body = text if is_md else f"```{'json' if rel.endswith('.json') else 'text'}\n{text.rstrip()}\n```\n"
    title = title_of(rel, text) if is_md else Path(rel).name
    if is_md:
        body = _FRONT.sub("", body, count=1)  # our front matter replaces the file's own (agents, skills)
    front = "\n".join(
        [
            "---",
            f'title: "{title}"',
            f"type: {kind}",
            f"source: {rel}",
            f"synced: {synced}",
            "tags: [" + ", ".join(tags) + "]",
            "---",
            "",
        ]
    )
    return front + body


def target_of(rel: str) -> Path:
    return VAULT / (rel if rel.endswith(".md") else rel + ".md")


def home(notes: list[tuple[str, str]]) -> str:
    groups: dict[str, list[tuple[str, str]]] = {}
    for rel, title in notes:
        groups.setdefault(note_type(rel), []).append((rel, title))
    order = [
        "readme",
        "rules",
        "doc",
        "command",
        "concept",
        "reference",
        "adr",
        "agent",
        "skill",
        "claude-command",
        "owner-doc",
        "schema",
        "golden",
        "license",
    ]
    lines = [
        "---",
        'title: "Sherpa knowledge base"',
        "type: home",
        "tags: [sherpa, home]",
        "---",
        "",
        "# Sherpa knowledge base",
        "",
        "Projection of the repository's docs, rules and harness — regenerated by `scripts/sync-kb.py`,",
        "never edited here. Edit the source file in the repository and sync again.",
        "",
    ]
    for kind in order:
        items = groups.get(kind)
        if not items:
            continue
        lines.append(f"## {kind}")
        lines.append("")
        for rel, title in items:
            link = rel if rel.endswith(".md") else rel + ".md"
            lines.append(f"- [{title}]({link}) — `{rel}`")
        lines.append("")
    return "\n".join(lines)


def sync(vault: Path, check: bool) -> int:
    global VAULT
    VAULT = vault
    dates = last_commit_dates()
    wanted: dict[Path, str] = {}
    notes: list[tuple[str, str]] = []
    for src in sources():
        rel = src.relative_to(ROOT).as_posix()
        text = src.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
        wanted[target_of(rel)] = render(rel, text, dates.get(rel, "uncommitted"))
        notes.append((rel, title_of(rel, text) if rel.endswith(".md") else Path(rel).name))
    wanted[vault / "Home.md"] = home(notes)
    existing = {p for p in vault.rglob("*.md") if p.is_file()} if vault.is_dir() else set()
    stale = sorted(existing - set(wanted))
    changed = sorted(p for p, content in wanted.items() if not p.is_file() or p.read_text(encoding="utf-8") != content)
    if check:
        for p in changed:
            print(f"out of date: {p.relative_to(vault)}")
        for p in stale:
            print(f"stale: {p.relative_to(vault)}")
        return 1 if changed or stale else 0
    for p in changed:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(wanted[p], encoding="utf-8", newline="\n")
    for p in stale:
        p.unlink()
    for d in sorted({p.parent for p in stale}, key=lambda d: -len(d.parts)):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    where = vault.relative_to(ROOT) if vault.is_relative_to(ROOT) else vault
    print(f"sync-kb: {len(wanted)} notes in {where} — {len(changed)} written, {len(stale)} removed")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vault", default=str(VAULT), help="vault directory (default: kb-sherpa/ in the repo)")
    ap.add_argument("--check", action="store_true", help="report what would change; exit 1 when out of date")
    args = ap.parse_args(argv)
    return sync(Path(args.vault).resolve(), args.check)


if __name__ == "__main__":
    os.chdir(ROOT)
    sys.exit(main())
