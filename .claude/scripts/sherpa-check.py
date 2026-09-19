#!/usr/bin/env python3
"""sherpa check — structural rules for a harness under ``.claude/`` (deterministic, seconds, no LLM).

This file is deliberately a single stdlib-only module: ``sherpa apply`` deploys a copy of it into the target repo
as ``.claude/scripts/sherpa-check.py`` so the rules run without an installed sherpa (CI, colleagues). The copy
delegates to the installed ``sherpa.check`` when one is importable — installed rules are never older than the
copy, and there is exactly one implementation (ADR-0013). It also owns the managed-block grammar and the content
hash that ``sherpa apply`` and ``sherpa status`` use, so drift is measured with the same code that checks it.

Rules (FAIL = exit 1, WARN informational):

  C1 agent-frontmatter   every .claude/agents/*.md has front matter with name and description
  C2 skill-frontmatter   every .claude/skills/*/SKILL.md and .agents/skills/*/SKILL.md has name and description
  C3 manifest-paths      every path under knowledge.always / knowledge.on_demand exists (relative to .claude/)
  C4 links               relative file links in .claude/**, .agents/**, CLAUDE.md and AGENTS.md files resolve
  C5 blocks              sherpa:begin/end markers are balanced, named and unique per file
  C6 hooks               .claude/settings.json is valid JSON and every hook command under $CLAUDE_PROJECT_DIR exists
  C7 budgets (WARN)      agent > 150 lines, owner doc > 600, skill > 250 — a fat agent is a rotation candidate;
                         a nested CLAUDE.md/AGENTS.md > 8 KiB, the root one > 32 KiB — runtimes inject them whole
  C8 drift (WARN)        with .sherpa/state.json: managed files/blocks whose hash differs, or that are missing

Scope (ADR-0047): with a state, C1 to C5 FAIL only in files sherpa generated (``origin: generated`` in the
state); in every other file under the homes — adopted or unrecorded, yours either way — they are WARN
``(yours)``, so the exit code says whether *sherpa's* harness is consistent, not whether a note somebody
vendored has a dead link. ``--strict`` makes them FAIL everywhere; without a state everything is strict.

Usage: ``python3 sherpa-check.py [repo] [--json] [--strict]``; from sherpa: ``sherpa check [repo] [--strict]``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SHERPA_VERSION = "0.7.8"  # replaced with the real version when the file is deployed into a repo

FAIL, WARN = "FAIL", "WARN"
BUDGETS = {"agent": 150, "owner-doc": 600, "skill": 250}  # lines; from harness practice, generic numbers
# Proximity files in bytes (ADR-0029): a nested CLAUDE.md/AGENTS.md lands whole in the context (Hermes: in a tool
# result on the first touch of the directory, ceiling 32 KiB, ~8 KiB recommended); the root file on every turn.
PROXIMITY_BUDGETS = {"nested": 8 * 1024, "root": 32 * 1024}

# A managed block: everything between two marker lines. Markdown uses HTML comments, YAML front matter uses "#".
MARKER = re.compile(r"^[ \t]*(?:<!--|#)[ \t]*sherpa:(begin|end)[ \t]+([A-Za-z0-9_-]+)[ \t]*(?:-->)?[ \t]*$")
_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
_FRONT = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.S)
_PROJECT_DIR = re.compile(r"\$\{?CLAUDE_PROJECT_DIR\}?/([^\"' ]+)")


@dataclass(frozen=True)
class Finding:
    level: str  # FAIL | WARN
    rule: str  # C1 … C8
    path: str  # repo-relative, "/" separated
    message: str

    def __str__(self) -> str:
        return f"{self.level} {self.rule} {self.path}: {self.message}"


# ---------------------------------------------------------------- shared primitives (used by sherpa.apply)


def content_hash(text: str) -> str:
    """Hash of the content with line endings normalised — git autocrlf must not look like a hand edit."""
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()[:16]


def parse_blocks(text: str) -> dict[str, tuple[int, int]]:
    """name → (index of the begin line, index of the end line). Raises ValueError on broken markers."""
    lines = text.split("\n")
    spans: dict[str, tuple[int, int]] = {}
    open_: tuple[str, int] | None = None
    for i, line in enumerate(lines):
        m = MARKER.match(line)
        if not m:
            continue
        kind, name = m.group(1), m.group(2)
        if kind == "begin":
            if open_:
                raise ValueError(f"line {i + 1}: begin {name} inside open block {open_[0]}")
            if name in spans:
                raise ValueError(f"line {i + 1}: duplicate block {name}")
            open_ = (name, i)
        else:
            if not open_ or open_[0] != name:
                raise ValueError(f"line {i + 1}: end {name} without matching begin")
            spans[name] = (open_[1], i)
            open_ = None
    if open_:
        raise ValueError(f"block {open_[0]} is never closed")
    return spans


def block_contents(text: str) -> dict[str, str]:
    """name → inner text (without the marker lines)."""
    lines = text.split("\n")
    return {n: "\n".join(lines[b + 1 : e]) for n, (b, e) in parse_blocks(text).items()}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


# ---------------------------------------------------------------- front matter (only what the rules need)


def front_matter(text: str) -> dict[str, object] | None:
    """Minimal YAML subset: ``key: value`` at the top level, one level of nested keys, ``- item`` lists, ``[]``.
    Enough for agent and skill front matter; None = no front matter."""
    m = _FRONT.match(text)
    if not m:
        return None
    out: dict[str, object] = {}
    section: str | None = None  # current top-level key
    sub: str | None = None  # current nested key under it
    for raw in m.group(1).split("\n"):
        line = "" if raw.lstrip().startswith("#") else raw.split(" #", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        body = line.strip()
        if body.startswith("- "):
            item = body[2:].strip().strip("'\"")
            holder = out.get(section) if section else None
            if isinstance(holder, dict) and sub is not None:
                lst = holder.setdefault(sub, [])
                if isinstance(lst, list):
                    lst.append(item)
            elif section and isinstance(holder, list):
                holder.append(item)
            elif section:
                out[section] = [item]
            continue
        key, _, value = body.partition(":")
        if indent == 0:
            section, sub = key.strip(), None
            out[section] = _scalar(value, empty={})
        elif section is not None and isinstance(out.get(section), dict):
            sub = key.strip()
            out[section][sub] = _scalar(value, empty=[])  # type: ignore[index]
    return out


def _scalar(value: str, *, empty: object) -> object:
    v = value.strip()
    if v == "[]":
        return []
    return empty if not v else v.strip("'\"")


# ---------------------------------------------------------------- rules


SKIP_DIRS = {"node_modules", "vendor", "target", "bin", "obj", "dist", "build", ".venv", ".git", "packages", ".sherpa"}


def _md_files(root: Path) -> list[Path]:
    """Harness markdown: everything under .claude/ and .agents/, plus every CLAUDE.md and AGENTS.md in the tree
    (root and nested proximity files), skipping dependency and build directories."""
    files: set[Path] = set()
    for home in (".claude", ".agents"):
        d = root / home
        if d.is_dir():
            files.update(p for p in d.rglob("*.md") if p.is_file())
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for p in entries:
            if p.is_dir():
                if p.name not in SKIP_DIRS and not (p.name.startswith(".") and p != root):
                    stack.append(p)
            elif p.name in ("CLAUDE.md", "AGENTS.md"):
                files.add(p)
    return sorted(files)


def _rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix()


def _kind_of(rel: str) -> str | None:
    if rel.startswith(".claude/agents/") and rel.endswith(".md"):
        return "agent"
    if rel.startswith((".claude/docs/modules/", ".agents/docs/modules/")) and rel.endswith(".md"):
        return "owner-doc"
    if rel.startswith((".claude/skills/", ".agents/skills/")) and rel.endswith("/SKILL.md"):
        return "skill"
    return None


def _managed_paths(root: Path) -> set[str] | None:
    """The files sherpa generated (``origin: generated`` in the state); None without a readable state — then
    nothing is managed yet and every rule is strict. Adopted files are yours (ADR-0007): their findings are hints."""
    state_path = root / ".sherpa" / "state.json"
    if not state_path.is_file():
        return None
    try:
        files = json.loads(read_text(state_path)).get("files")
    except ValueError:
        return None
    if not isinstance(files, dict):
        return None
    return {p for p, rec in files.items() if isinstance(rec, dict) and rec.get("origin") == "generated"}


def check(
    root: Path,
    *,
    strict: bool = False,
    managed_too: frozenset[str] | set[str] = frozenset(),
    yours_now: frozenset[str] | set[str] = frozenset(),
) -> list[Finding]:
    """``managed_too``: paths treated as sherpa's although the state does not record them yet — ``apply`` checks
    what it writes before it writes the state; on a first ``apply`` they are the only managed files.
    ``yours_now``: paths the state still records but ``apply`` is handing back (ADR-0048) — theirs already."""
    root = root.resolve()
    managed = None if strict else _managed_paths(root)
    if managed_too and not strict:
        managed = (managed or set()) | set(managed_too)
    if managed is not None:
        managed -= set(yours_now)
    claude = root / ".claude"
    findings: list[Finding] = []
    for p in _md_files(root):
        rel = _rel(root, p)
        text = read_text(p)
        own = _check_file(rel, p, text, claude)
        findings.extend(_scope(own, managed is None or rel in managed))
    findings.extend(_check_hooks(root))
    findings.extend(_check_drift(root))
    findings.sort(key=lambda f: (f.level != FAIL, f.rule, f.path, f.message))
    return findings


def _scope(found: list[Finding], managed: bool) -> list[Finding]:
    """C1 to C5 in a file sherpa did not generate are WARN ``(yours)`` (ADR-0047)."""
    if managed:
        return found
    return [Finding(WARN, f.rule, f.path, f.message + " (yours)") if f.level == FAIL else f for f in found]


def _check_file(rel: str, p: Path, text: str, claude: Path) -> list[Finding]:
    """C1 to C5 and C7 for one file."""
    findings: list[Finding] = []
    kind = _kind_of(rel)
    fm = front_matter(text)
    if kind in ("agent", "skill"):
        rule = "C1" if kind == "agent" else "C2"
        if fm is None:
            findings.append(Finding(FAIL, rule, rel, "no front matter (name, description required)"))
        else:
            for key in ("name", "description"):
                if not fm.get(key):
                    findings.append(Finding(FAIL, rule, rel, f"front matter has no {key}"))
    if kind == "agent" and isinstance(fm, dict) and isinstance(fm.get("knowledge"), dict):
        for lst in fm["knowledge"].values():  # type: ignore[union-attr]
            for item in lst if isinstance(lst, list) else []:
                if not (claude / item).exists():
                    findings.append(Finding(FAIL, "C3", rel, f"knowledge path {item} does not exist"))
    for m in _LINK.finditer(text) if "/archive/" not in rel else ():  # history may tell the old state
        href = m.group(1).split("#", 1)[0]
        if not href or "://" in href or href.startswith(("mailto:", "/")) or "." not in href.rsplit("/", 1)[-1]:
            continue  # only file links; a target without an extension is a wiki page or an anchor, not a file
        if not (p.parent / href).exists():
            findings.append(Finding(FAIL, "C4", rel, f"link target {href} does not exist"))
    try:
        parse_blocks(text)
    except ValueError as e:
        findings.append(Finding(FAIL, "C5", rel, f"managed block markers: {e}"))
    if kind and (n := text.count("\n") + 1) > BUDGETS[kind]:
        findings.append(Finding(WARN, "C7", rel, f"{n} lines > budget {BUDGETS[kind]} ({kind})"))
    if p.name in ("CLAUDE.md", "AGENTS.md"):
        where = "root" if "/" not in rel else "nested"
        if (size := len(text.encode("utf-8"))) > PROXIMITY_BUDGETS[where]:
            msg = f"{size} bytes > budget {PROXIMITY_BUDGETS[where] // 1024} KiB ({where} proximity file)"
            findings.append(Finding(WARN, "C7", rel, msg))
    return findings


def _check_hooks(root: Path) -> list[Finding]:
    settings = root / ".claude" / "settings.json"
    if not settings.is_file():
        return []
    rel = ".claude/settings.json"
    try:
        data = json.loads(read_text(settings))
    except ValueError as e:
        return [Finding(FAIL, "C6", rel, f"not valid JSON: {e}")]
    out = []
    for event, groups in (data.get("hooks") or {}).items():
        for group in groups if isinstance(groups, list) else []:
            for hook in group.get("hooks", []) if isinstance(group, dict) else []:
                for m in _PROJECT_DIR.finditer(str(hook.get("command", ""))):
                    if not (root / m.group(1)).exists():
                        out.append(Finding(FAIL, "C6", rel, f"{event} hook references missing file {m.group(1)}"))
    return out


def _check_drift(root: Path) -> list[Finding]:
    state_path = root / ".sherpa" / "state.json"
    if not state_path.is_file():
        return []
    try:
        state = json.loads(read_text(state_path))
    except ValueError as e:
        return [Finding(FAIL, "C8", ".sherpa/state.json", f"not valid JSON: {e}")]
    out = []
    for rel, rec in sorted((state.get("files") or {}).items()):
        p = root / rel
        if not p.is_file():
            out.append(Finding(WARN, "C8", rel, "missing (in state, not on disk)"))
            continue
        if rec.get("origin") == "adopted":
            continue  # yours by definition (ADR-0007): a changed hash is not drift
        text = read_text(p)
        if rec.get("hash") and rec.get("mode") != "blocks" and content_hash(text) != rec["hash"]:
            out.append(Finding(WARN, "C8", rel, "hand-edited (hash differs from state)"))
        if rec.get("blocks"):
            try:
                have = block_contents(text)
            except ValueError:
                continue  # C5 reports the broken markers
            for name, h in sorted(rec["blocks"].items()):
                if name not in have:
                    out.append(Finding(WARN, "C8", rel, f"block {name} removed"))
                elif content_hash(have[name]) != h:
                    out.append(Finding(WARN, "C8", rel, f"block {name} hand-edited"))
    return out


def render(findings: list[Finding], root: Path) -> str:
    n_fail = sum(f.level == FAIL for f in findings)
    n_warn = len(findings) - n_fail
    lines = [f"sherpa check {root}: {n_fail} FAIL, {n_warn} WARN"]
    lines.extend(f"  {f}" for f in findings)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = [a for a in (argv if argv is not None else sys.argv[1:])]
    as_json, strict = "--json" in args, "--strict" in args
    args = [a for a in args if a not in ("--json", "--strict")]
    root = Path(args[0]) if args else Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".")
    findings = check(root, strict=strict)
    if as_json:
        sys.stdout.write(json.dumps([f.__dict__ for f in findings], indent=2) + "\n")
    else:
        sys.stdout.write(render(findings, root.resolve()))
    return 1 if any(f.level == FAIL for f in findings) else 0


if __name__ == "__main__":
    # Deployed copy: prefer the installed sherpa (its rules are never older). SHERPA_CHECK_STANDALONE=1 forces the copy.
    if os.environ.get("SHERPA_CHECK_STANDALONE") != "1":
        try:
            from sherpa import check as _installed  # type: ignore

            if Path(_installed.__file__).resolve() != Path(__file__).resolve():
                sys.exit(_installed.main())
        except ImportError:
            pass
    sys.exit(main())
