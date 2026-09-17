"""Stage-1 rules. One function per building block; all work on ``Unit`` (a module or a directory without one).

Decisions (owned by this module, ADR-0006/0011/0012):
- **Units**: every module (T1) plus every depth-1 directory that no module covers, is not a dot directory and
  reaches ``dir_min_files``. A root module covers everything — then there are no directory units.
- **Ranking**: over non-test units that are not generator-dominated; ties by id. Quartile = rank ≤
  ceil(n · agent_top). Generator-dominated units take no rank away (CodeScene excludes generated code before
  scoring hotspots).
- **Dormant units** (0 commits/90d and 0 dependents) get no owner doc — visible as a no with a flip criterion,
  never silently. **Small units** (fewer than ``owner_doc_min_files`` files and no dependents) neither: a doc
  nobody links to is the first to go stale; a dependent overrides the floor.
- **Generator-dominated** (share of generator output ≥ generated_share): no agent, no librarian; the skill for the
  generator takes over (principle: generated code is regenerated, not explained).
- **Test infrastructure**: the most active test unit is proposed when it has more commits than any business unit —
  blind spot number one in harness analysis practice.
- **No's only within reach**: an agent/librarian no is listed when the unit meets the rank criterion or the commit
  floor — there the flip criterion is real information. All other units are counted in one ``notes`` line. Dormant
  and generator-dominated units are always listed (the reader must know).
- **Skill evidence**: generated files from the floor up; config alone counts only for families without detectable
  output (OpenAPI clients) — an Angular config without checked-in bundles is not a skill.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fnmatch import fnmatchcase

from sherpa.config import PlanConfig
from sherpa.model import GeneratorStat, Model, ModuleStat, SubDir
from sherpa.plan import PROPOSE, SKIP, Check, Entry, Plan
from sherpa.scan.t1_modules import SUB_DIR_DEPTH, TEST_DIR_NAMES

MAX_NAMED = 12  # names in a note; the entries themselves list every unit

COST = {
    "outcome": "hook set, label file, harness_rev in the state",
    "owner-doc": "1 owner doc (skeleton + scanner facts, maintained by sherpa)",
    "agent": "1 agent with knowledge manifest, 1 eval catalogue from the graph",
    "librarian": "1 scheduled task, 1 SKILL file, anchor upkeep per run",
    "test-infra": "1 owner doc for the test infrastructure, librarian candidate",
    "skill": "1 SKILL file: source, config, regeneration command",
}


@dataclass(frozen=True)
class Unit:
    id: str
    kind: str  # module | dir
    path: str
    files: int
    loc: int
    generated_files: int
    commits_90d: int
    commits_30d: int
    authors_90d: int
    dependents: int
    is_test: bool

    @property
    def generated_share(self) -> float:
        return self.generated_files / self.files if self.files else 0.0

    @property
    def dormant(self) -> bool:
        return self.commits_90d == 0 and self.dependents == 0


def sub_units_of(m: ModuleStat, cfg: PlanConfig, *, why: str = "") -> tuple[list[Unit], str | None]:
    """Sub-units of a single-manifest repository (ADR-0020) or of a dominant root module (ADR-0027). The depth
    rule: the first depth below the module's path at which at least two directories are *source directories* —
    ≥ 2 files in the module's language, a package for Python — test directories excluded. ``[plan] units =
    [globs]`` replaces the rule; an empty list switches sub-units off. Returns the units and a one-line
    explanation for the plan notes."""

    def unit(s: SubDir) -> Unit:
        return Unit(s.path, "dir", s.path, s.files, s.loc, 0, s.commits_90d, s.commits_30d, s.authors_90d, 0, False)

    def is_test_dir(path: str) -> bool:
        return any(part in TEST_DIR_NAMES for part in path.split("/"))

    if cfg.units is not None:
        chosen = sorted((s for s in m.sub_dirs if any(fnmatchcase(s.path, g) for g in cfg.units)), key=lambda s: s.path)
        if not chosen:
            return [], None
        return [unit(s) for s in chosen], f"{len(chosen)} sub-units of {m.id} from sherpa.toml [plan] units"
    for depth in range(1, SUB_DIR_DEPTH + 1):
        candidates = [
            s
            for s in m.sub_dirs
            if s.depth == depth
            and s.source_files >= 2
            and (s.package or m.kind != "python")
            and not is_test_dir(s.path)
            and not s.path.rsplit("/", 1)[-1].startswith(".")
        ]
        if len(candidates) >= 2:
            candidates.sort(key=lambda s: s.path)
            names = ", ".join(s.path for s in candidates[:MAX_NAMED])
            return [unit(s) for s in candidates], (
                f"{len(candidates)} sub-units of {m.id}{why} by the depth rule (depth {depth}): {names} — "
                "[plan] units in sherpa.toml overrides the rule."
            )
    return [], None


def units_of(model: Model, cfg: PlanConfig) -> list[Unit]:
    units, _ = units_and_note(model, cfg)
    return units


def units_and_note(model: Model, cfg: PlanConfig) -> tuple[list[Unit], str | None]:
    units = [
        Unit(
            m.id,
            "module",
            m.path,
            m.files,
            m.loc,
            m.generated_files,
            m.commits_90d,
            m.commits_30d,
            m.authors_90d,
            len(m.dependents),
            m.is_test,
        )
        for m in model.modules
    ]
    covered = [m.path for m in model.modules]
    if "" in covered:
        root = next(m for m in model.modules if m.path == "")
        total = sum(m.files for m in model.modules)
        # The only module (ADR-0020), or the catch-all that holds most of the repository (ADR-0027): sub-units.
        if len(model.modules) == 1:
            return (units + (r := sub_units_of(root, cfg))[0]), r[1]
        if total and root.files / total >= cfg.root_share:
            why = f" ({root.files / total:.0%} of the files, root_share {cfg.root_share:g})"
            subs, note = sub_units_of(root, cfg, why=why)
            return units + subs, note
        return units, None
    for d in model.git.dirs:
        p = d.path
        if not p or "/" in p or p.startswith(".") or d.files < cfg.dir_min_files:
            continue
        if any(c == p or c.startswith(p + "/") for c in covered):
            continue
        is_test = p.lower() in ("test", "tests", "spec", "specs")
        units.append(
            Unit(
                p, "dir", p, d.files, d.loc, d.generated_files, d.commits_90d, d.commits_30d, d.authors_90d, 0, is_test
            )
        )
    return units, None


def _rank(units: list[Unit], key: str) -> dict[str, int]:
    order = sorted(units, key=lambda u: (-getattr(u, key), u.id))
    return {u.id: i + 1 for i, u in enumerate(order)}


def _evidence(u: Unit) -> dict[str, object]:
    return {
        "path": u.path,
        "files": u.files,
        "generated_files": u.generated_files,
        "commits_90d": u.commits_90d,
        "commits_30d": u.commits_30d,
        "authors_90d": u.authors_90d,
        "dependents": u.dependents,
    }


def _reason(checks: list[Check], prefix: str = "") -> str | None:
    failed = [c for c in checks if not c.ok]
    if not failed:
        return None
    missing = ", ".join(c.label for c in failed)
    flip = " and ".join(c.need for c in failed if c.need)
    return f"{prefix}{missing}." + (f" Flips when: {flip}" if flip else "")


def _entry(kind: str, u: Unit, checks: list[Check], *, reason_prefix: str = "", extra: dict | None = None) -> Entry:
    ok = all(c.ok for c in checks)
    return Entry(
        kind=kind,
        target=u.id,
        scope=u.path,
        default=PROPOSE if ok else SKIP,
        evidence={**_evidence(u), **(extra or {})},
        checks=tuple(checks),
        cost=COST[kind],
        reason=None if ok else _reason(checks, reason_prefix),
    )


def outcome_entry(model: Model) -> Entry:
    return Entry(
        kind="outcome",
        target=model.repo,
        scope="",
        default=PROPOSE,
        evidence={"commits_90d": model.git.commits_90d, "authors_90d": model.git.authors_90d},
        checks=(Check("mandatory: no harness without an outcome signal (ADR-0008)", True),),
        cost=COST["outcome"],
    )


def owner_doc_entry(u: Unit, cfg: PlanConfig) -> Entry:
    """Dormant units get no doc; small units without dependents neither — a two-file tool is explained where it is
    used, and a doc nobody links to is the first to go stale. A dependent overrides the floor."""
    checks = [
        Check(
            f"{u.commits_90d} commits/90d, {u.dependents} dependents",
            not u.dormant,
            "commits/90d ≥ 1 or dependents ≥ 1",
        ),
        Check(f"{u.files} files", not small_unit(u, cfg), f"files ≥ {cfg.owner_doc_min_files} or dependents ≥ 1"),
    ]
    prefix = "dormant: " if u.dormant else "small unit: " if small_unit(u, cfg) else ""
    return _entry("owner-doc", u, checks, reason_prefix=prefix)


def small_unit(u: Unit, cfg: PlanConfig) -> bool:
    return u.files < cfg.owner_doc_min_files and u.dependents == 0


def _generated_check(u: Unit, cfg: PlanConfig) -> Check:
    return Check(
        f"{u.generated_files}/{u.files} files generated ({round(100 * u.generated_share)} %)",
        False,
        f"generated share < {round(100 * cfg.generated_share)} %",
    )


def _generated_prefix(gen: GeneratorStat | None) -> str:
    hint = f" — see skill regenerate-{gen.family}" if gen else ""
    return f"the knowledge lives in the generator{hint}: "


def agent_entry(u: Unit, rank: int, n: int, cfg: PlanConfig, gen: GeneratorStat | None) -> Entry:
    if u.generated_share >= cfg.generated_share:
        return _entry("agent", u, [_generated_check(u, cfg)], reason_prefix=_generated_prefix(gen))
    k = math.ceil(n * cfg.agent_top)
    checks = [
        Check(f"rank {rank}/{n} churn", rank <= k, f"rank ≤ {k} by commits/90d"),
        Check(
            f"{u.commits_90d} commits/90d",
            u.commits_90d >= cfg.agent_min_commits_90d,
            f"commits/90d ≥ {cfg.agent_min_commits_90d}",
        ),
        Check(f"{u.files} files", u.files >= cfg.agent_min_files, f"files ≥ {cfg.agent_min_files}"),
        Check(
            f"{u.authors_90d} authors",
            u.authors_90d >= cfg.agent_min_authors_90d,
            f"authors/90d ≥ {cfg.agent_min_authors_90d}",
        ),
    ]
    return _entry("agent", u, checks, extra={"rank_commits_90d": f"{rank}/{n}"})


def librarian_entry(u: Unit, rank: int, n: int, cfg: PlanConfig, gen: GeneratorStat | None) -> Entry:
    if u.generated_share >= cfg.generated_share:
        return _entry("librarian", u, [_generated_check(u, cfg)], reason_prefix=_generated_prefix(gen))
    floor = u.commits_30d >= cfg.librarian_min_commits_30d or u.commits_90d >= cfg.librarian_min_commits_90d
    checks = [
        Check(f"rank {rank}/{n} momentum", rank <= cfg.librarian_top_n, f"top {cfg.librarian_top_n} by commits/30d"),
        Check(
            f"{u.commits_30d} commits/30d, {u.commits_90d}/90d",
            floor,
            f"commits/30d ≥ {cfg.librarian_min_commits_30d} or commits/90d ≥ {cfg.librarian_min_commits_90d}",
        ),
    ]
    return _entry("librarian", u, checks, extra={"rank_commits_30d": f"{rank}/{n}"})


def test_infra_entry(t: Unit, top: Unit | None) -> Entry:
    if top is None:
        checks = [
            Check(
                f"{t.commits_90d} commits/90d",
                t.commits_90d > 0,
                "commits/90d ≥ 1 (no business unit to compare with)",
            )
        ]
    else:
        checks = [
            Check(
                f"{t.commits_90d} commits/90d vs. {top.commits_90d} ({top.id})",
                t.commits_90d >= top.commits_90d,
                "commits/90d ≥ most active business unit",
            )
        ]
    return _entry("test-infra", t, checks, extra={"compared_to": top.id if top else None})


def skill_evidence(g: GeneratorStat, cfg: PlanConfig) -> bool:
    from sherpa.scan.generators import FAMILY_BY_ID

    fam = FAMILY_BY_ID.get(g.family)
    config_counts = fam is not None and not fam.generated  # output not detectable by path → config is evidence
    return g.generated_files >= cfg.skill_min_generated_files or (config_counts and bool(g.configs))


def skill_entry(g: GeneratorStat, cfg: PlanConfig) -> Entry:
    checks = [
        Check(
            f"{g.generated_files} generated files, {len(g.configs)} configs",
            skill_evidence(g, cfg),
            f"generated files ≥ {cfg.skill_min_generated_files} (or config when output is not detectable)",
        )
    ]
    ok = all(c.ok for c in checks)
    return Entry(
        kind="skill",
        target=f"regenerate-{g.family}",
        scope=g.home,
        default=PROPOSE if ok else SKIP,
        evidence={
            "family": g.family,
            "title": g.title,
            "module": g.module,
            "home": g.home,
            "generated_files": g.generated_files,
            "generated_loc": g.generated_loc,
            "sources": list(g.sources),
            "configs": list(g.configs),
            "command": g.command,
        },
        checks=tuple(checks),
        cost=COST["skill"],
        reason=None if ok else _reason(checks),
    )


def build(model: Model, cfg: PlanConfig) -> Plan:
    units, units_note = units_and_note(model, cfg)
    by_module_gen: dict[str, GeneratorStat] = {}  # largest generator per module, for the hint in the no
    for g in sorted(model.generators, key=lambda g: (-g.generated_files, g.family)):
        if g.module and g.skill:
            by_module_gen.setdefault(g.module, g)

    business = [u for u in units if not u.is_test]
    rankable = [u for u in business if u.generated_share < cfg.generated_share]
    r90, r30 = _rank(rankable, "commits_90d"), _rank(rankable, "commits_30d")
    n = len(rankable)
    top = max(rankable, key=lambda u: (u.commits_90d, u.id), default=None)

    k = math.ceil(n * cfg.agent_top)
    entries: list[Entry] = [outcome_entry(model)]
    out_of_reach = {"agent": 0, "librarian": 0}
    for u in sorted(business, key=lambda u: (-u.commits_90d, u.id)):
        gen = by_module_gen.get(u.id)
        entries.append(owner_doc_entry(u, cfg))
        if u.dormant:
            continue  # dormant: agent/librarian would merely repeat the owner-doc no
        generated = u.generated_share >= cfg.generated_share
        a = agent_entry(u, r90.get(u.id, 0), n, cfg, gen)
        if a.default == PROPOSE or generated or r90[u.id] <= k or u.commits_90d >= cfg.agent_min_commits_90d:
            entries.append(a)
        else:
            out_of_reach["agent"] += 1
        li = librarian_entry(u, r30.get(u.id, 0), n, cfg, gen)
        floor = u.commits_30d >= cfg.librarian_min_commits_30d or u.commits_90d >= cfg.librarian_min_commits_90d
        if li.default == PROPOSE or generated or r30[u.id] <= cfg.librarian_top_n or floor:
            entries.append(li)
        else:
            out_of_reach["librarian"] += 1

    tests = [u for u in units if u.is_test]
    if tests:
        entries.append(test_infra_entry(max(tests, key=lambda u: (u.commits_90d, u.id)), top))

    below: dict[str, int] = {}
    for g in model.generators:
        if not g.skill:
            continue
        if skill_evidence(g, cfg):
            entries.append(skill_entry(g, cfg))
        else:
            below[g.family] = below.get(g.family, 0) + 1

    kind_order = {k: i for i, k in enumerate(("outcome", "owner-doc", "agent", "librarian", "test-infra", "skill"))}
    entries.sort(key=lambda e: (e.default != PROPOSE, kind_order[e.kind], _pos(e, r90)))

    dormant = sorted(u.id for u in business if u.dormant)
    notes = [units_note] if units_note else []
    if dormant:
        names = ", ".join(dormant[:MAX_NAMED]) + (
            f", … (+{len(dormant) - MAX_NAMED} more)" if len(dormant) > MAX_NAMED else ""
        )
        notes.append(
            f"{len(dormant)} dormant units without owner doc (0 commits/90d, 0 dependents): "
            f"{names} — the first commit turns them into a proposal; each is listed above as a no."
        )
    small = sorted(u.id for u in business if not u.dormant and small_unit(u, cfg))
    if small:
        names = ", ".join(small[:MAX_NAMED]) + (
            f", … (+{len(small) - MAX_NAMED} more)" if len(small) > MAX_NAMED else ""
        )
        notes.append(
            f"{len(small)} small units without owner doc (< {cfg.owner_doc_min_files} files, 0 dependents): {names} — "
            "listed above as no's; owner_doc_min_files in sherpa.toml [plan] moves the floor, a dependent overrides it."
        )
    if out_of_reach["agent"] or out_of_reach["librarian"]:
        notes.append(
            f"not listed, out of reach: {out_of_reach['agent']} units for agent "
            f"(rank > {k} and < {cfg.agent_min_commits_90d} commits/90d), {out_of_reach['librarian']} for librarian "
            f"(rank > {cfg.librarian_top_n} and below both floors)."
        )
    if below:
        notes.append(
            "generator traces below the floor (no skill): "
            + ", ".join(f"{f} ×{c}" for f, c in sorted(below.items()))
            + f" — floor: {cfg.skill_min_generated_files} generated files."
        )

    return Plan(
        repo=model.repo,
        model={
            "trunk": model.git.trunk.ref,
            "rev": model.git.trunk.rev,
            "as_of": model.git.windows.as_of,
            "sherpa": model.sherpa,
        },
        thresholds=cfg.thresholds(),
        ranking={
            "commits_90d": [u.id for u in sorted(rankable, key=lambda u: r90[u.id])],
            "commits_30d": [u.id for u in sorted(rankable, key=lambda u: r30[u.id])],
        },
        entries=entries,
        notes=notes,
    )


def _pos(e: Entry, r90: dict[str, int]) -> tuple[int, str]:
    return (r90.get(e.target, 10**9), e.target + e.scope)
