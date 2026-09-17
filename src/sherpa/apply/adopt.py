"""``sherpa adopt`` — an existing harness enters the state, not a byte of it changes (ADR-0007, ADR-0017).

The model is ``terraform import``: what is already there becomes known to Sherpa without being touched. Three
things happen, all deterministic and all from the files:

1. **Inventory** — every file under ``.claude/`` and ``.agents/`` plus every ``CLAUDE.md``/``AGENTS.md`` in the
   tree is classified by its path (agent, skill, command, doc, hook, settings, script, eval, root, nested,
   unknown). Unknown is a kind, not a guess.
2. **Reconcile** — where the plan renders a file at the same path, the file is compared with the rendering:
   byte-equal → recorded as ``generated`` (the state is rebuilt from the source of truth); marked blocks that
   equal their rendering → recorded per block; anything else stays what it is. Base files sherpa names itself
   (checker copy, outcome hook, telemetry ignore) are sherpa's by name, so an older copy gets refreshed by the
   next ``apply``. Files ``apply`` may still add to — a root or nested ``CLAUDE.md``/``AGENTS.md`` without
   markers, ``settings.json`` without the hook — are left unrecorded so that ``apply`` can append its block.
3. **Link** — an adopted agent or doc is linked to a unit of the plan: by name (file stem = unit slug) or by the
   unit path it mentions most (at least twice, unambiguous). A linked file **covers** the plan entry: ``sherpa
   plan`` shows ``[covered by …]``, ``apply`` renders nothing for it.

What adopt cannot know it says: a block that differs from the current rendering may be a hand edit or an older
rendering — it stays as it is either way. Gaps (fat agents without a manifest, docs that match no unit, units the
plan proposes an owner doc for and nothing exists) are reported, never fixed silently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from sherpa import __version__, gitinfo
from sherpa.apply import state as state_mod
from sherpa.apply.render import Target, modernize_stamp, slug
from sherpa.apply.state import ADOPTED, BLOCKS, GENERATED, JSON_HOOKS, MANAGED, FileRecord, State
from sherpa.check import BUDGETS, SKIP_DIRS, block_contents, content_hash, front_matter
from sherpa.plan import PROPOSE, Plan

KINDS = (
    "root",
    "nested",
    "agent",
    "skill",
    "command",
    "doc",
    "hook",
    "settings",
    "script",
    "eval",
    "sherpa",
    "unknown",
)
HOMES = (".claude", ".agents")
PRIVATE = {".claude/settings.local.json"}  # personal by Claude Code convention, never part of the harness
ADOPT, REBUILT, UNRECORDED, UNKNOWN = "a", "=", "·", "?"


@dataclass(frozen=True)
class Found:
    path: str  # repo-relative, "/" separated
    kind: str
    lines: int
    text: str
    name: str | None = None  # front matter ``name``
    manifest: bool = False  # front matter has ``knowledge`` (the facts live elsewhere)
    markers: bool = False  # contains sherpa block markers


@dataclass
class Adoption:
    files: dict[str, FileRecord]
    rows: list[tuple[str, str, str, str]] = field(default_factory=list)  # (op, path, kind, detail)
    gaps: list[str] = field(default_factory=list)
    kept: int = 0  # generated records whose hashes still match
    rebuilt: int = 0  # generated records recovered from the rendering
    adopted: int = 0
    dropped: list[str] = field(default_factory=list)  # records of files that are gone
    covered: int = 0

    def counts(self) -> str:
        return f"{self.adopted} adopted, {self.rebuilt} rebuilt, {self.kept} kept, {len(self.dropped)} dropped"


# ---------------------------------------------------------------- inventory


def kind_of(rel: str) -> str:
    parts = rel.split("/")
    name = parts[-1]
    if name in ("CLAUDE.md", "AGENTS.md"):
        return "root" if len(parts) == 1 else "nested"
    if parts[0] == ".sherpa":
        return "sherpa"  # the telemetry ignore file — sherpa's own, outside the homes
    if parts[0] not in HOMES or len(parts) < 2:
        return "unknown"
    home, sub = parts[0], parts[1]
    if name == "SKILL.md" and "skills" in parts[1:-1]:
        return "skill"
    if home == ".claude" and sub == "agents" and name.endswith(".md"):
        return "agent"
    if home == ".claude" and sub == "commands" and name.endswith(".md"):
        return "command"
    if home == ".claude" and sub == "hooks":
        return "hook"
    if home == ".claude" and rel == ".claude/settings.json":
        return "settings"
    if sub == "docs" and name.endswith(".md"):
        return "doc"
    if sub == "scripts":
        return "script"
    if sub in ("evals", "eval"):
        return "eval"
    return "unknown"


def inventory(repo: Path, extra: frozenset[str] | set[str] = frozenset()) -> list[Found]:
    """Every harness file: the two homes, every CLAUDE.md/AGENTS.md in the tree, plus ``extra`` paths that exist
    (rendered targets outside the homes, e.g. the telemetry ignore file). Git-ignored files are not the harness."""
    paths: set[str] = set()
    for home in HOMES:
        d = repo / home
        if d.is_dir():
            paths.update(_rel(repo, p) for p in _walk(d))
    for p in _walk(repo, names={"CLAUDE.md", "AGENTS.md"}):
        paths.add(_rel(repo, p))
    paths.update(x for x in extra if (repo / x).is_file())
    paths -= PRIVATE
    paths -= gitinfo.ignored(repo, sorted(paths))  # personal files (memory, local settings) are not the harness
    return [_found(repo, rel) for rel in sorted(paths)]


def _walk(root: Path, names: set[str] | None = None) -> list[Path]:
    out: list[Path] = []
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for p in entries:
            if p.is_dir():
                if p.name in SKIP_DIRS or (names is not None and p.name.startswith(".") and p != root):
                    continue
                stack.append(p)
            elif p.is_file() and (names is None or p.name in names):
                out.append(p)
    return out


def _rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix()


def _found(repo: Path, rel: str) -> Found:
    text = (repo / rel).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    kind = kind_of(rel)
    fm = front_matter(text) if rel.endswith(".md") else None
    name = fm.get("name") if isinstance(fm, dict) and isinstance(fm.get("name"), str) else None
    return Found(
        rel,
        kind,
        text.count("\n") + 1,
        text,
        name,
        bool(fm and "knowledge" in fm),
        "sherpa:begin" in text,
    )


# ---------------------------------------------------------------- linking


_MENTION_TAIL = r"(?![\w.\-])"


def link(f: Found, units: dict[str, str]) -> tuple[str | None, str]:
    """(unit id, why) — by name first, else the unit path mentioned most (≥ 2, unambiguous); else nothing."""
    stem = Path(f.path).parent.name if f.kind == "skill" else Path(f.path).stem
    by_slug = {slug(u): u for u in units}
    if stem in by_slug:
        return by_slug[stem], "name matches"
    if f.name and slug(f.name) in by_slug:
        return by_slug[slug(f.name)], "front matter name matches"
    counts = []
    for u, path in units.items():
        if not path:
            continue
        n = len(re.findall(re.escape(path) + _MENTION_TAIL, f.text))
        if n:
            counts.append((n, len(path), u, path))
    counts.sort(key=lambda c: (-c[0], -c[1], c[2]))
    if not counts or counts[0][0] < 2:
        return None, "no unit matches"
    top = counts[0]
    if len(counts) > 1 and counts[1][0] == top[0] and not top[3].startswith(counts[1][3]):
        return None, f"ambiguous: {top[2]} and {counts[1][2]} mentioned {top[0]}× each"
    return top[2], f"mentions {top[3]} {top[0]}×"


# ---------------------------------------------------------------- adopt


def adopt(
    repo: Path,
    plan: Plan,
    targets: list[Target],
    previous: State,
    *,
    home: str,
    runtime_targets: tuple[str, ...],
    version: str = __version__,
) -> Adoption:
    rendered = {t.path: t for t in targets}
    found = inventory(repo, {t.path for t in targets})
    units = {e.target: e.scope for e in plan.entries if e.kind in ("owner-doc", "test-infra")}
    keys = {(e.kind, e.target): f"{e.kind}:{e.target}:{e.scope}" for e in plan.entries}
    proposed_agents = {e.target for e in plan.entries if e.kind == "agent" and e.default == PROPOSE}
    files: dict[str, FileRecord] = {}
    a = Adoption(files)
    for f in found:
        prev = previous.files.get(f.path)
        if prev is not None and prev.origin == GENERATED and _still_matches(prev, f.text):
            files[f.path] = prev
            a.kept += 1
            a.rows.append((REBUILT, f.path, f.kind, "sherpa's, unchanged"))
            continue
        t = rendered.get(f.path)
        if t is not None:
            rec, detail = _reconcile(t, f)
            if rec is None:
                a.rows.append((UNRECORDED, f.path, f.kind, detail))
                continue
            files[f.path] = rec
            if rec.origin == GENERATED:
                a.rebuilt += 1
                a.rows.append((REBUILT, f.path, f.kind, detail))
            else:
                a.adopted += 1
                a.rows.append((ADOPT, f.path, f.kind, detail))
            continue
        if f.kind in ("root", "nested") and not f.markers:
            a.rows.append((UNRECORDED, f.path, f.kind, "no sherpa markers — `apply` appends its block (ADR-0016)"))
            continue
        entry, detail = _link_entry(f, units, keys)
        files[f.path] = FileRecord(MANAGED, ADOPTED, entry, content_hash(f.text))
        a.adopted += 1
        a.rows.append((UNKNOWN if f.kind == "unknown" else ADOPT, f.path, f.kind, detail))
        if f.kind == "agent" and entry:
            unit = entry.split(":")[1]
            if unit not in proposed_agents:
                a.gaps.append(f"{f.path}: agent for `{unit}` — the plan proposes none (below the threshold); yours")
    a.dropped = sorted(p for p in previous.files if p not in files and not (repo / p).is_file())
    _gaps(a, found, files, plan)
    a.covered = sum(1 for r in files.values() if r.origin == ADOPTED and r.entry in set(keys.values()))
    return a


def _still_matches(rec: FileRecord, text: str) -> bool:
    if rec.mode in (MANAGED, JSON_HOOKS):
        return content_hash(text) == rec.hash
    try:
        have = block_contents(text)
    except ValueError:
        return False
    return all(n in have and content_hash(have[n]) == h for n, h in rec.blocks.items())


def _reconcile(t: Target, f: Found) -> tuple[FileRecord | None, str]:
    """The file against its rendering: what equals the rendering is sherpa's; the rest is not."""
    if t.mode == MANAGED:
        if f.text == t.content:
            return FileRecord(MANAGED, GENERATED, t.entry, content_hash(f.text)), "sherpa's, matches the plan"
        if modernize_stamp(f.text) == t.content:
            return FileRecord(
                MANAGED, GENERATED, t.entry, content_hash(f.text)
            ), "sherpa's, older stamp — `apply` refreshes it"
        if t.entry is None:  # checker copy, hook, ignore file: sherpa's by name, refreshed by the next apply
            return FileRecord(MANAGED, GENERATED, None, content_hash(f.text)), "sherpa's by name — `apply` refreshes it"
        return FileRecord(MANAGED, ADOPTED, t.entry, content_hash(f.text)), "at sherpa's path, yours — covers the entry"
    if t.mode == JSON_HOOKS:
        if "sherpa-outcome.py" in f.text:
            return FileRecord(JSON_HOOKS, GENERATED, None, content_hash(f.text)), "hook present"
        return None, "no sherpa hook — `apply` merges it in"
    try:
        have = block_contents(f.text)
    except ValueError as e:
        return None, f"markers broken: {e}"
    if not have:
        if t.append:
            return None, "no sherpa markers — `apply` appends its block (ADR-0016)"
        return FileRecord(MANAGED, ADOPTED, t.entry, content_hash(f.text)), "at sherpa's path, yours — covers the entry"
    known = {n: content_hash(have[n]) for n, v in t.blocks.items() if n in have and have[n] == v}
    # An older stamp format is still sherpa's rendering (ADR-0022): recorded with the bytes on disk, so the next
    # apply sees "unchanged since the state" and rewrites it in the current form.
    older = {
        n: content_hash(have[n])
        for n, v in t.blocks.items()
        if n in have and n not in known and modernize_stamp(have[n]) == v
    }
    known.update(older)
    stale = [n for n in t.blocks if n in have and n not in known]
    detail = f"{len(known)} of {len(t.blocks)} blocks match the plan"
    if older:
        detail += f"; block {', '.join(older)} carries an older stamp — `apply` refreshes it"
    if stale:
        detail += f"; block {', '.join(stale)} differs (hand edit) — stays"
    return FileRecord(BLOCKS, GENERATED, t.entry, blocks=known), detail


def _link_entry(f: Found, units: dict[str, str], keys: dict[tuple[str, str], str]) -> tuple[str | None, str]:
    if f.kind not in ("agent", "doc"):
        return None, "yours"
    unit, why = link(f, units)
    if unit is None:
        return None, why
    kind = "agent" if f.kind == "agent" else ("test-infra" if ("test-infra", unit) in keys else "owner-doc")
    return f"{kind}:{unit}:{units[unit]}", f"→ {kind} {unit} ({why})"


def _gaps(a: Adoption, found: list[Found], files: dict[str, FileRecord], plan: Plan) -> None:
    for f in found:
        if f.kind == "agent" and f.lines > BUDGETS["agent"] and not f.manifest:
            a.gaps.append(
                f"{f.path}: {f.lines} lines, no knowledge manifest — rotation candidate, facts belong in an owner doc"
            )
        rec = files.get(f.path)
        if f.kind == "doc" and rec is not None and rec.origin == ADOPTED and rec.entry is None:
            a.gaps.append(f"{f.path}: no unit matches by name or path mentions — moved, renamed or not a module doc")
    present = {r.entry for r in files.values() if r.entry}  # generated or adopted, either way a doc exists
    open_docs = [
        e
        for e in plan.entries
        if e.kind in ("owner-doc", "test-infra")
        and e.default == PROPOSE
        and e.decision != "reject"
        and f"{e.kind}:{e.target}:{e.scope}" not in present
    ]
    if open_docs:
        a.gaps.append(f"{_n(len(open_docs), 'proposed owner doc')} without an existing doc — `apply` creates them")
    unknown = [f.path for f in found if f.kind == "unknown"]
    if unknown:
        a.gaps.append(f"{_n(len(unknown), 'file')} of unknown kind — recorded as yours, listed above with `?`")


def _n(n: int, noun: str) -> str:
    return f"{n} {noun}" + ("" if n == 1 else "s")


# ---------------------------------------------------------------- state


def new_state(a: Adoption, plan: Plan, previous: State, *, home: str, targets: tuple[str, ...]) -> State:
    return State(
        harness_rev=state_mod.harness_rev(a.files),
        plan={k: str(v) for k, v in plan.model.items() if k in ("trunk", "rev", "as_of")},
        applied_at=state_mod.now_iso(),
        files=a.files,
        home=home,
        targets=tuple(targets),
    )


# ---------------------------------------------------------------- console


def render(a: Adoption, *, home: str, targets: tuple[str, ...]) -> str:
    lines = [f"sherpa adopt — home {home} · targets {', '.join(targets)}: {len(a.rows)} harness files"]
    if a.rows:
        w_path = min(max(len(p) for _, p, _, _ in a.rows), 56)
        w_kind = max(len(k) for _, _, k, _ in a.rows)
        lines.extend(f"  {op} {p:<{w_path}}  {k:<{w_kind}}  {d}" for op, p, k, d in a.rows)
    if a.dropped:
        lines.append(f"dropped from the state (file gone): {', '.join(a.dropped)}")
    if a.gaps:
        lines.append("gaps:")
        lines.extend(f"  - {g}" for g in a.gaps)
    return "\n".join(lines) + "\n"


__all__ = ["KINDS", "Adoption", "Found", "adopt", "inventory", "kind_of", "link", "new_state", "render"]
