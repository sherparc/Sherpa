"""``sherpa adopt`` — an existing harness enters the state, not a byte of it changes (ADR-0007, ADR-0017).

The model is ``terraform import``: what is already there becomes known to Sherpa without being touched. Three
things happen, all deterministic and all from the files:

1. **Inventory** — every file under ``.claude/`` and ``.agents/`` plus every ``CLAUDE.md``/``AGENTS.md`` in the
   tree is classified by its path (agent, skill, command, doc, hook, settings, script, eval, root, nested,
   unknown). Unknown is a kind, not a guess.
2. **Reconcile** — where the plan renders a file at the same path, the file is compared with the rendering:
   byte-equal → recorded as ``generated`` (the state is rebuilt from the source of truth); marked blocks that
   equal their rendering → recorded per block; anything else stays what it is — a base file sherpa names itself (checker
   copy, outcome hook, telemetry ignore) included: adopt cannot tell an older copy from a hand edit, so a
   differing one is yours and listed as a gap with the way to a fresh one (ADR-0033). Files ``apply`` may still
   add to — a root or nested ``CLAUDE.md``/``AGENTS.md`` without markers, ``settings.json`` without the hook —
   are left unrecorded so that ``apply`` can append its block.
3. **Link** — an adopted agent or doc is linked to a unit of the plan: by name (file stem = unit slug) or by the
   unit path it mentions most (at least twice, unambiguous). A linked file **covers** the plan entry: ``sherpa
   plan`` shows ``[covered by …]``, ``apply`` renders nothing for it. Stronger than any link: a nested
   ``AGENTS.md`` whose directory is a unit's own path covers the unit's owner-doc entry by path (ADR-0049) —
   the file stays unrecorded so ``apply`` still appends its facts block, and the plan entry gets
   ``covered: <path>``, kept like a hand-written one.

What adopt cannot know it says: a block that differs from the current rendering may be a hand edit or an older
rendering — it stays as it is either way. Gaps (fat agents without a manifest, docs that match no unit, units the
plan proposes an owner doc for and nothing exists) are reported, never fixed silently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path

from sherpa import __version__, gitinfo
from sherpa.apply import state as state_mod
from sherpa.apply.render import Target, modernize, slug
from sherpa.apply.state import ADOPTED, BLOCKS, GENERATED, JSON_HOOKS, MANAGED, FileRecord, State
from sherpa.check import BUDGETS, SKIP_DIRS, block_contents, content_hash, front_matter, parse_blocks
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
    path_covers: dict[str, str] = field(default_factory=dict)  # entry address → nested AGENTS.md (ADR-0049)

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


def own_prose(text: str) -> str:
    """What the team wrote: the file without sherpa's blocks, markers included. Empty for a file that is nothing
    but sherpa's block — and for broken markers, which are not a doc either way."""
    try:
        spans = parse_blocks(text)
    except ValueError:
        return ""
    inside = {i for b, e in spans.values() for i in range(b, e + 1)}
    return "\n".join(line for i, line in enumerate(text.split("\n")) if i not in inside).strip()


def covers_by_path(plan: Plan, found: list[Found]) -> dict[str, str]:
    """A nested ``AGENTS.md`` whose directory is a unit's own path covers the unit's owner-doc entry — an exact
    match on the path, no heuristic (ADR-0049; Backstage: the file next to the code is the owner). It beats a
    name or mention link; only the team's own word beats it, so entries with a ``decision:`` or a ``covered:``
    naming another file are left alone. The team's doc is a file with prose of its own outside sherpa's markers
    — before ``apply`` appended its facts block and after, so the cover is the same fact on every run and a
    lost ``.sherpa/`` rebuilds it from the files (ADR-0017); a file that is nothing but sherpa's block is
    sherpa's own proximity file and covers nothing. The root ``AGENTS.md`` is the harness index and covers
    nothing; a nested ``CLAUDE.md`` is runtime-specific and covers nothing. Returns entry address → path."""
    by_scope = {
        e.scope: e
        for e in plan.entries
        if e.kind in ("owner-doc", "test-infra")
        and e.scope
        and e.decision is None
        and e.covered in (None, f"{e.scope}/AGENTS.md")
    }
    out: dict[str, str] = {}
    for f in found:
        if f.kind == "nested" and f.path.endswith("/AGENTS.md"):
            e = by_scope.get(f.path.rsplit("/", 1)[0])
            if e is not None and (not f.markers or e.covered == f.path or own_prose(f.text)):
                out[e.address] = f.path
    return out


def _covers(address: str) -> str:
    return f"covers {' '.join(address.split(':')[:2])} (the unit's own path)"


def _cover_row(address: str, scope: str, runtime_targets: tuple[str, ...]) -> str:
    """The row for a covering file without markers (ADR-0049): unrecorded stays unrecorded — the facts land in
    it with the agents-md target, in the nested CLAUDE.md with claude only; the prose stays the team's."""
    if "agents-md" in runtime_targets:
        return f"{_covers(address)} — `apply` appends its facts block"
    return f"{_covers(address)} — the facts go to {scope}/CLAUDE.md"


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
    deselected: list[Target] | None = None,
) -> Adoption:
    """``deselected``: what sherpa would render for entries the plan no longer selects (rejected, covered, gone
    from the trunk) — a file that equals such a rendering is sherpa's leftover, recorded as generated so that
    ``apply`` removes it, never adopted as yours and never a cover (ADR-0048, F25)."""
    rendered = {t.path: t for t in targets}
    leftovers = {t.path: t for t in deselected or () if t.path not in rendered}
    found = inventory(repo, {t.path for t in targets} | set(leftovers))
    units = {e.target: e.scope for e in plan.entries if e.kind in ("owner-doc", "test-infra")}
    keys = {(e.kind, e.target): f"{e.kind}:{e.target}:{e.scope}" for e in plan.entries}
    proposed_agents = {e.target for e in plan.entries if e.kind == "agent" and e.default == PROPOSE}
    by_hand = {e.covered: e.address for e in plan.entries if e.covered}  # the plan's word beats the heuristic
    covers = covers_by_path(plan, found)  # entry address → nested AGENTS.md; beats the heuristic (ADR-0049)
    cover_of = {path: address for address, path in covers.items()}
    demoted: set[str] = set()  # files that lost their entry to a by-path cover — the row says why, no gap
    files: dict[str, FileRecord] = {}
    ranks: dict[str, int] = {}  # linked file → 0 by the plan, 1 by name, 2 by mentions
    a = Adoption(files, path_covers=covers)
    for f in found:
        prev = previous.files.get(f.path)
        if prev is not None and prev.origin == GENERATED and _still_matches(prev, f.text):
            files[f.path] = prev
            a.kept += 1
            a.rows.append((REBUILT, f.path, f.kind, "sherpa's, unchanged"))
            continue
        if (t := leftovers.get(f.path)) is not None and (rec := _leftover(t, f)) is not None:
            files[f.path] = rec
            a.rebuilt += 1
            a.rows.append((REBUILT, f.path, f.kind, "sherpa's, no longer in the plan — `apply` removes it"))
            continue
        address = cover_of.get(f.path)
        if address is not None and not f.markers:  # the team's doc at the unit's own path: never recorded
            a.rows.append((UNRECORDED, f.path, f.kind, _cover_row(address, f.path.rsplit("/", 1)[0], runtime_targets)))
            continue
        t = rendered.get(f.path)
        if t is not None:
            rec, detail = _reconcile(t, f)
            if address is not None:
                detail += f"; {_covers(address)}"
            if rec is None:
                a.rows.append((UNRECORDED, f.path, f.kind, detail))
                continue
            if rec.origin == ADOPTED and rec.entry in covers:
                # the nested AGENTS.md at the unit's own path covers the entry — this file stays the team's,
                # linked to nothing (ADR-0049: by-path beats at-sherpa's-path and name/mention links)
                detail = f"at sherpa's path, yours — {covers[rec.entry]} covers it (the unit's own path)"
                demoted.add(f.path)
                rec = replace(rec, entry=None)
            files[f.path] = rec
            if rec.origin == GENERATED:
                a.rebuilt += 1
                a.rows.append((REBUILT, f.path, f.kind, detail))
            else:
                a.adopted += 1
                a.rows.append((ADOPT, f.path, f.kind, detail))
                if rec.entry:
                    ranks[f.path] = 1  # at sherpa's path: as good as a name match
            continue
        if f.kind in ("root", "nested") and not f.markers:
            a.rows.append((UNRECORDED, f.path, f.kind, "no sherpa markers — `apply` appends its block (ADR-0016)"))
            continue
        if f.path in by_hand:
            entry, detail = by_hand[f.path], f"→ {' '.join(by_hand[f.path].split(':')[:2])} (covered: set in the plan)"
            ranks[f.path] = 0
        else:
            entry, detail = _link_entry(f, units, keys)
            if entry:
                if entry in covers:
                    detail = (
                        f"{detail.replace('→ ', 'matches ', 1)} — yours, {covers[entry]} covers it "
                        "(the unit's own path)"
                    )
                    demoted.add(f.path)
                    entry = None
                else:
                    ranks[f.path] = 1 if "name matches" in detail else 2
        files[f.path] = FileRecord(MANAGED, ADOPTED, entry, content_hash(f.text))
        a.adopted += 1
        a.rows.append((UNKNOWN if f.kind == "unknown" else ADOPT, f.path, f.kind, detail))
        if f.kind == "agent" and entry:
            unit = entry.split(":")[1]
            if unit not in proposed_agents:
                a.gaps.append(f"{f.path}: agent for `{unit}` — the plan proposes none (below the threshold); yours")
    _one_cover_per_entry(files, ranks, a)
    a.dropped = sorted(p for p in previous.files if p not in files and not (repo / p).is_file())
    _gaps(a, found, files, plan, {t.path for t in targets if t.mode == MANAGED and t.entry is None}, version, demoted)
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
        if modernize(f.text) == t.content:
            return FileRecord(
                MANAGED, GENERATED, t.entry, content_hash(f.text)
            ), "sherpa's, older stamp — `apply` refreshes it"
        if t.entry is None:  # checker copy, hook, ignore file that differs: a hand edit or an older copy — yours
            return FileRecord(MANAGED, ADOPTED, None, content_hash(f.text)), "differs from sherpa's copy — yours"
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
        if n in have and n not in known and modernize(have[n]) == v
    }
    known.update(older)
    stale = [n for n in t.blocks if n in have and n not in known]
    if not stale and f.text == t.content:  # the seed and every block: sherpa's whole (ADR-0048)
        return FileRecord(BLOCKS, GENERATED, t.entry, content_hash(f.text), blocks=known), "sherpa's, matches the plan"
    if not stale and modernize(f.text) == t.content:  # an older stamp or seed: still sherpa's whole (ADR-0022)
        what = f"block {', '.join(older)} carries an older stamp" if older else "an older seed"
        return FileRecord(
            BLOCKS, GENERATED, t.entry, content_hash(f.text), blocks=known
        ), f"sherpa's, {what} — `apply` refreshes it"
    detail = f"{len(known)} of {len(t.blocks)} blocks match the plan"
    if older:
        detail += f"; block {', '.join(older)} carries an older stamp — `apply` refreshes it"
    if stale:
        detail += f"; block {', '.join(stale)} differs (hand edit) — stays"
    return FileRecord(BLOCKS, GENERATED, t.entry, blocks=known), detail


def is_owner_doc_location(path: str) -> bool:
    """Only a doc under ``<home>/docs/modules/`` can be an owner doc (ADR-0046): reference pages, archives and
    reports mention modules too and were linked as covers before."""
    parts = path.split("/")
    return len(parts) == 4 and parts[0] in HOMES and parts[1:3] == ["docs", "modules"]


def _leftover(t: Target, f: Found) -> FileRecord | None:
    """Sherpa's own rendering of an entry no longer selected — byte for byte or up to an older stamp — as a
    generated record; anything else is not provably sherpa's and goes the normal way."""
    if t.mode == MANAGED:
        if f.text == t.content or modernize(f.text) == t.content:
            return FileRecord(MANAGED, GENERATED, t.entry, content_hash(f.text))
        return None
    if t.mode == JSON_HOOKS:
        return None  # the hook record is a base record, never an entry's
    try:
        have = block_contents(f.text)
    except ValueError:
        return None
    known = {
        n: content_hash(have[n]) for n, v in t.blocks.items() if n in have and (have[n] == v or modernize(have[n]) == v)
    }
    if not known:
        return None
    whole = f.text == t.content or modernize(f.text) == t.content
    return FileRecord(BLOCKS, GENERATED, t.entry, content_hash(f.text) if whole else None, blocks=known)


def _link_entry(f: Found, units: dict[str, str], keys: dict[tuple[str, str], str]) -> tuple[str | None, str]:
    if f.kind not in ("agent", "doc") or (f.kind == "doc" and not is_owner_doc_location(f.path)):
        return None, "yours"
    unit, why = link(f, units)
    if unit is None:
        return None, why
    kind = "agent" if f.kind == "agent" else ("test-infra" if ("test-infra", unit) in keys else "owner-doc")
    return f"{kind}:{unit}:{units[unit]}", f"→ {kind} {unit} ({why})"


def _one_cover_per_entry(files: dict[str, FileRecord], ranks: dict[str, int], a: Adoption) -> None:
    """Several linked files for one entry: the plan's own ``covered:`` beats a name match, a name match beats a
    mention count; equals are a decision the plan must take — none covers, the gap names them (ADR-0046)."""
    by_entry: dict[str, list[str]] = {}
    for path, rec in files.items():
        if rec.origin == ADOPTED and rec.entry and path in ranks:
            by_entry.setdefault(rec.entry, []).append(path)
    for entry, paths in sorted(by_entry.items()):
        if len(paths) < 2:
            continue
        best = min(ranks[p] for p in paths)
        winners = sorted(p for p in paths if ranks[p] == best)
        losers = [p for p in paths if p not in winners] + (winners if len(winners) > 1 else [])
        for p in losers:
            files[p] = FileRecord(MANAGED, ADOPTED, None, files[p].hash)
        a.rows = [
            (
                op,
                p,
                k,
                d.replace("→ ", "matches ", 1)
                + (" — yours, another file covers the entry" if len(winners) == 1 else " — yours, see gaps"),
            )
            if p in losers
            else (op, p, k, d)
            for op, p, k, d in a.rows
        ]
        if len(winners) > 1:
            what = " ".join(entry.split(":")[:2])
            a.gaps.append(
                f"{len(winners)} files match {what} ({', '.join(winners)}) — none covers it; name the owner doc "
                "on the entry: `covered: <path>`"
            )


def _gaps(
    a: Adoption,
    found: list[Found],
    files: dict[str, FileRecord],
    plan: Plan,
    base_paths: set[str],
    version: str,
    demoted: set[str],
) -> None:
    for f in found:
        if f.kind == "agent" and f.lines > BUDGETS["agent"] and not f.manifest:
            a.gaps.append(
                f"{f.path}: {f.lines} lines, no knowledge manifest — rotation candidate, facts belong in an owner doc"
            )
        rec = files.get(f.path)
        if (
            f.kind == "doc"
            and rec is not None
            and rec.origin == ADOPTED
            and rec.entry is None
            and f.path not in demoted  # lost to a by-path cover — the row already says so (ADR-0049)
        ):
            a.gaps.append(
                f"{f.path}: no unit matches by name or path mentions — moved, renamed or not a module doc; "
                "if it is the owner doc of a unit, name it on that entry: `covered: <path>`"
            )
        if rec is not None and rec.origin == ADOPTED and rec.entry is None and f.path in base_paths:
            a.gaps.append(
                f"{f.path}: differs from sherpa {version}'s copy — yours; delete it and run `apply` for the current one"
            )
    present = {r.entry for r in files.values() if r.entry}  # generated or adopted, either way a doc exists
    open_docs = [
        e
        for e in plan.entries
        if e.kind in ("owner-doc", "test-infra")
        and e.default == PROPOSE
        and e.decision != "reject"
        and e.address not in present
        and e.covered is None  # a cover the state does not carry: by hand outside the homes, or by path (ADR-0049)
        and e.address not in a.path_covers
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


__all__ = [
    "KINDS",
    "Adoption",
    "Found",
    "adopt",
    "inventory",
    "kind_of",
    "link",
    "new_state",
    "render",
]
