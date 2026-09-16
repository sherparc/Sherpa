"""``sherpa plan`` stage 1: rules, reach, generators, YAML round trip, decision keeping, goldens, CLI."""

from __future__ import annotations

import os
import re
from dataclasses import replace
from pathlib import Path

import pytest

from sherpa import __version__
from sherpa.cli import main
from sherpa.config import PlanConfig, load
from sherpa.model import Conventions, DirStat, GeneratorStat, GitLayer, Model, ModuleStat, TrunkInfo, Windows
from sherpa.plan import PROPOSE, SKIP, Check, Entry, build_plan, render_console, yamlio
from sherpa.plan.rules import Unit, units_of
from sherpa.scan import scan
from tests.conftest import commit, git
from tests.test_t1_modules import poly_repo  # noqa: F401 — fixture

GOLDENS = Path(__file__).parent / "goldens"


# ---------------------------------------------------------------- synthetic models


def mod(
    id_: str,
    path: str,
    *,
    c90=0,
    c30=0,
    authors=0,
    files=10,
    gen=0,
    deps=(),
    dependents=(),
    is_test=False,
    kind="dotnet",
):
    return ModuleStat(
        id=id_,
        path=path,
        kind=kind,
        manifest=f"{path}/m",
        is_test=is_test,
        files=files,
        loc=files * 10,
        test_files=0,
        generated_files=gen,
        deps=list(deps),
        dependents=list(dependents),
        tested_by=[],
        commits_90d=c90,
        commits_30d=c30,
        authors_90d=authors,
        hotspots=[],
    )


def dir_(path: str, *, files=20, c90=0, c30=0, authors=0, gen=0):
    return DirStat(path, files, files * 10, gen, c90, c30, authors)


def model(modules=(), dirs=(), generators=(), repo="Shop"):
    return Model(
        sherpa=__version__,
        schema_version=3,
        repo=repo,
        origin="x",
        git=GitLayer(
            trunk=TrunkInfo("origin/main", "origin/HEAD", "a" * 40),
            windows=Windows("2026-03-01T00:00:00Z", "2025-12-01T00:00:00Z", "2026-01-30T00:00:00Z"),
            commits_total=10,
            commits_90d=sum(m.commits_90d for m in modules),
            commits_30d=0,
            authors_90d=3,
            first_commit="2025-01-01T00:00:00Z",
            last_commit="2026-03-01T00:00:00Z",
            files=[],
            dirs=list(dirs),
            hotspots=[],
        ),
        modules=list(modules),
        generators=list(generators),
        conventions=Conventions({}, [], []),
    )


def by_kind(plan, kind):
    return {e.target: e for e in plan.entries if e.kind == kind}


# ---------------------------------------------------------------- units


def test_units_modules_plus_uncovered_dirs_without_dot_dirs():
    m = model(
        modules=[mod("A", "src/A", c90=5), mod("T", "tests/T", is_test=True)],
        dirs=[
            dir_(""),
            dir_("src", c90=5),
            dir_("src/A"),
            dir_("tests"),
            dir_("infra", files=12, c90=3, authors=2),
            dir_(".release-markers", files=100, c90=300),
            dir_("tiny", files=3),
            dir_("docs", files=50),
        ],
    )
    ids = {u.id: u for u in units_of(m, PlanConfig())}
    assert set(ids) == {"A", "T", "infra", "docs"}
    assert ids["infra"].kind == "dir" and ids["infra"].authors_90d == 2 and not ids["infra"].is_test
    assert ids["T"].is_test


def test_units_root_module_covers_everything():
    m = model(modules=[mod("root", "", c90=5)], dirs=[dir_("infra", files=50, c90=9)])
    assert [u.id for u in units_of(m, PlanConfig())] == ["root"]


def test_unit_generated_share_and_dormant():
    u = Unit(
        "x",
        "module",
        "x",
        files=0,
        loc=0,
        generated_files=0,
        commits_90d=0,
        commits_30d=0,
        authors_90d=0,
        dependents=0,
        is_test=False,
    )
    assert u.generated_share == 0.0 and u.dormant
    assert replace(u, dependents=1).dormant is False and replace(u, files=4, generated_files=3).generated_share == 0.75


# ---------------------------------------------------------------- rules


def big_model(n: int, active: int):
    """n modules; the first ``active`` meet all floors (descending commits), the rest is not dormant but small."""
    mods = []
    for i in range(n):
        c = 200 - i if i < active else 5
        mods.append(mod(f"M{i:02d}", f"src/M{i:02d}", c90=c, c30=c // 3, authors=4, files=40))
    return model(modules=mods)


def test_quartile_with_floor_small_repo_gets_an_agent_and_big_repo_is_capped():
    small = build_plan(
        model(modules=[mod(f"M{i}", f"src/M{i}", c90=30 - i, c30=12, authors=2, files=35) for i in range(5)])
    )
    agents = [e for e in by_kind(small, "agent").values() if e.default == PROPOSE]
    assert [e.target for e in agents] == ["M0", "M1"]  # ceil(5 * 0.25) = 2
    assert agents[0].evidence["rank_commits_90d"] == "1/5"
    big = build_plan(big_model(50, 50))
    assert sum(e.default == PROPOSE for e in by_kind(big, "agent").values()) == 13  # ceil(50 * 0.25)
    assert sum(e.default == PROPOSE for e in by_kind(big, "librarian").values()) == 2


def test_agent_skip_names_rank_and_floor_with_flip_criterion():
    m = model(
        modules=[
            mod("Big", "src/Big", c90=50, c30=10, authors=3, files=40),
            mod("Rep", "src/Rep", c90=25, c30=1, authors=1, files=40),  # within reach via the commit floor
        ]
    )
    e = by_kind(build_plan(m), "agent")["Rep"]
    assert e.default == SKIP
    assert e.summary == "rank 2/2 churn ✗ · 25 commits/90d ✓ · 40 files ✓ · 1 authors ✗"
    assert e.reason == "rank 2/2 churn, 1 authors. Flips when: rank ≤ 1 by commits/90d and authors/90d ≥ 2"
    assert set(e.evidence) == {
        "path",
        "files",
        "generated_files",
        "commits_90d",
        "commits_30d",
        "authors_90d",
        "dependents",
        "rank_commits_90d",
    }


def test_dormant_module_gets_visible_no_and_note_but_no_agent_or_librarian_entry():
    m = model(modules=[mod("Live", "src/Live", c90=30, c30=10, authors=2, files=40), mod("Idle", "src/Idle", files=9)])
    p = build_plan(m)
    e = by_kind(p, "owner-doc")["Idle"]
    assert e.default == SKIP and e.reason.startswith("dormant: 0 commits/90d, 0 dependents.")
    assert "Flips when: commits/90d ≥ 1 or dependents ≥ 1" in e.reason
    assert "Idle" not in by_kind(p, "agent") and "Idle" not in by_kind(p, "librarian")
    assert any(n.startswith("1 dormant units without owner doc") and "Idle" in n for n in p.notes)
    many = model([mod(f"m{i:02d}", f"m{i:02d}") for i in range(15)] + [mod("live", "live", c90=5)])
    (note,) = [n for n in build_plan(many).notes if n.startswith("15 dormant")]
    assert "m11, … (+3 more)" in note and "m12" not in note
    assert by_kind(p, "owner-doc")["Live"].default == PROPOSE


def test_dependent_only_module_is_not_dormant():
    m = model(modules=[mod("Core", "src/Core", dependents=("App",)), mod("App", "src/App", c90=3, deps=("Core",))])
    assert by_kind(build_plan(m), "owner-doc")["Core"].default == PROPOSE


def test_generated_dominated_module_gets_skill_instead_of_agent_and_no_rank():
    gen = GeneratorStat(
        "ef-migrations",
        "EF Core Migrations",
        "Mig",
        "src/Mig",
        380,
        50000,
        ["src/Mig/ShopDbContext.cs"],
        [],
        "dotnet ef migrations add <Name>",
        True,
    )
    m = model(
        modules=[
            mod("Mig", "src/Mig", c90=90, c30=40, authors=8, files=400, gen=380),
            mod("Pricing", "src/Pricing", c90=60, c30=20, authors=5, files=50),
        ],
        generators=[gen],
    )
    p = build_plan(m)
    a = by_kind(p, "agent")
    assert a["Mig"].default == SKIP and a["Mig"].summary == "380/400 files generated (95 %) ✗"
    assert (
        a["Mig"].reason
        == "the knowledge lives in the generator — see skill regenerate-ef-migrations: 380/400 files generated (95 %). Flips when: generated share < 50 %"
    )
    assert by_kind(p, "librarian")["Mig"].default == SKIP
    assert a["Pricing"].evidence["rank_commits_90d"] == "1/1"  # Mig takes no rank away
    assert p.ranking["commits_90d"] == ["Pricing"]
    s = by_kind(p, "skill")["regenerate-ef-migrations"]
    assert (s.default, s.scope, s.evidence["command"], s.evidence["sources"]) == (
        PROPOSE,
        "src/Mig",
        "dotnet ef migrations add <Name>",
        ["src/Mig/ShopDbContext.cs"],
    )
    assert by_kind(p, "owner-doc")["Mig"].default == PROPOSE  # the owner doc stays


def test_skill_evidence_config_only_counts_for_families_without_detectable_output():
    api = GeneratorStat(
        "openapi-client", "OpenAPI", "Api", "api", 0, 0, ["api/openapi.json"], ["api/nswag.json"], "nswag run", True
    )
    bundles = GeneratorStat("bundles", "Bundles", "Web", "web", 0, 0, [], ["web/angular.json"], "npm run build", True)
    few = GeneratorStat("resx", "ResX", "A", "src/A", 1, 5, ["src/A/R.resx"], [], "IDE", True)
    lock = GeneratorStat("lockfiles", "Lockfiles", None, "", 1, 0, [], [], "-", False)
    p = build_plan(model(modules=[mod("A", "src/A", c90=1)], generators=[api, bundles, few, lock]))
    skills = {(e.target, e.scope): e for e in p.entries if e.kind == "skill"}
    assert set(skills) == {("regenerate-openapi-client", "api")}
    assert skills[("regenerate-openapi-client", "api")].default == PROPOSE
    assert any(
        n == "generator traces below the floor (no skill): bundles ×1, resx ×1 — floor: 5 generated files."
        for n in p.notes
    )


def test_test_infra_proposed_when_more_active_than_any_business_unit():
    m = model(
        modules=[
            mod("Core", "src/Core", c90=50, c30=10, authors=3, files=40),
            mod("Tests", "tests/Tests", c90=60, is_test=True),
            mod("Small.Tests", "tests/S", c90=2, is_test=True),
        ]
    )
    p = build_plan(m)
    t = by_kind(p, "test-infra")
    assert list(t) == ["Tests"] and t["Tests"].default == PROPOSE
    assert t["Tests"].summary == "60 commits/90d vs. 50 (Core) ✓" and t["Tests"].evidence["compared_to"] == "Core"
    p2 = build_plan(
        model(
            modules=[
                mod("Core", "src/Core", c90=50, c30=10, authors=3, files=40),
                mod("Tests", "tests/Tests", c90=20, is_test=True),
            ]
        )
    )
    assert by_kind(p2, "test-infra")["Tests"].default == SKIP
    p3 = build_plan(model(modules=[mod("Tests", "tests/Tests", c90=3, is_test=True)]))
    assert by_kind(p3, "test-infra")["Tests"].default == PROPOSE and "no business unit" in str(
        by_kind(p3, "test-infra")["Tests"].checks[0]
    )


def test_out_of_reach_units_are_counted_not_listed():
    p = build_plan(big_model(50, 12))
    agents, libs = by_kind(p, "agent"), by_kind(p, "librarian")
    assert (
        len(agents) == 13 and len(libs) == 12
    )  # 13 in the quartile (12 propose + M12 with 5 commits at a quartile rank), 12 above the floor
    assert sum(e.default == SKIP for e in agents.values()) == 1
    assert any(n.startswith("not listed, out of reach: 37 units for agent") for n in p.notes)


def test_librarian_skip_lists_in_reach_units_with_momentum_rank():
    m = model(modules=[mod(f"M{i}", f"src/M{i}", c90=100, c30=50 - i, authors=3, files=40) for i in range(4)])
    libs = by_kind(build_plan(m), "librarian")
    assert [e.default for e in libs.values()] == [PROPOSE, PROPOSE, SKIP, SKIP]
    assert libs["M2"].summary == "rank 3/4 momentum ✗ · 48 commits/30d, 100/90d ✓"
    assert libs["M2"].reason == "rank 3/4 momentum. Flips when: top 2 by commits/30d"


def test_outcome_entry_is_first_and_mandatory():
    p = build_plan(model(modules=[mod("A", "src/A", c90=1)]))
    e = p.entries[0]
    assert (e.kind, e.target, e.default, e.decision) == ("outcome", "Shop", PROPOSE, None)
    assert e.checks[0].need == "" and str(e.checks[0]) == e.checks[0].short


def test_entries_sorted_proposals_first_then_kind_then_rank():
    p = build_plan(big_model(8, 8))
    kinds = [(e.default, e.kind) for e in p.entries]
    assert kinds == sorted(
        kinds,
        key=lambda t: (
            t[0] != PROPOSE,
            ["outcome", "owner-doc", "agent", "librarian", "test-infra", "skill"].index(t[1]),
        ),
    )
    assert [e.target for e in p.entries if e.kind == "owner-doc"] == [f"M{i:02d}" for i in range(8)]


def test_plan_is_deterministic_and_thresholds_recorded():
    m = big_model(6, 6)
    assert yamlio.dumps(build_plan(m)) == yamlio.dumps(build_plan(m))
    p = build_plan(m, PlanConfig(agent_top=0.5))
    assert p.thresholds["agent_top"] == 0.5 and p.model["rev"] == "a" * 40
    assert sum(e.default == PROPOSE for e in by_kind(p, "agent").values()) == 3


# ---------------------------------------------------------------- YAML


def test_yaml_roundtrip_validates_and_keeps_field_order():
    p = build_plan(big_model(3, 3))
    text = yamlio.dumps(p)
    assert text.startswith("# harness-plan — generated by sherpa ")
    assert text.index("kind: owner-doc") < text.index("target: M00") < text.index("evidence: {path: src/M00")
    data = yamlio.loads(text)
    assert data["schema_version"] == 1 and len(data["entries"]) == len(p.entries)
    e = yamlio.entry_from_dict(next(d for d in data["entries"] if d["kind"] == "agent"))
    assert e.checks[0] == Check("rank 1/3 churn", True, "rank ≤ 1 by commits/90d") and e.decision is None


def test_yaml_load_rejects_non_plan_and_bad_decision(tmp_path: Path):
    with pytest.raises(ValueError, match="not a plan"):
        yamlio.loads("- a\n- b\n")
    with pytest.raises(ValueError, match="decision 'maybe'"):
        yamlio.decisions_of({"entries": [{"kind": "agent", "target": "A", "scope": "", "decision": "maybe"}]})


def test_merge_decisions_keeps_by_key_and_counts():
    p = build_plan(big_model(3, 3))
    text = yamlio.dumps(p).replace(
        "target: M00\n  scope: src/M00\n  default: propose\n  decision: null",
        "target: M00\n  scope: src/M00\n  default: propose\n  decision: accept",
        1,
    )
    prev = yamlio.loads(text)
    merged, n = yamlio.merge_decisions(p, prev)
    assert n == 1 and merged.entries[1].decision == "accept" and merged.entries[2].decision is None
    assert yamlio.merge_decisions(p, None) == (p, 0)
    stale = {"entries": [{"kind": "agent", "target": "Gone", "scope": "x", "decision": "reject"}]}
    assert yamlio.merge_decisions(p, stale)[1] == 0


def test_render_console_marks_decisions_and_notes():
    p = build_plan(model(modules=[mod("A", "src/A", c90=1), mod("Idle", "src/Idle")]))
    p.entries[1] = Entry(
        *(
            getattr(p.entries[1], f)
            for f in ("kind", "target", "scope", "default", "evidence", "checks", "cost", "reason")
        ),
        decision="accept",
    )
    out = render_console(p, "harness-plan.yaml")
    assert out.startswith("harness-plan.yaml — 2 proposals, 3 reasoned no's\n")  # Idle dormant; A: agent, librarian
    assert "  + owner-doc  A     1 commits/90d, 0 dependents ✓ [accept]\n" in out
    assert "  - owner-doc  Idle  0 commits/90d, 0 dependents ✗\n" in out
    assert out.rstrip().endswith("— the first commit turns them into a proposal; each is listed above as a no.")


# ---------------------------------------------------------------- configuration


def test_plan_config_from_toml_and_unknown_key(tmp_path: Path):
    (tmp_path / "sherpa.toml").write_text("[plan]\nagent_top = 0.5\nlibrarian_top_n = 3\n")
    c = load(tmp_path).plan
    assert (c.agent_top, c.librarian_top_n, c.agent_min_files) == (0.5, 3, 30)
    (tmp_path / "sherpa.toml").write_text("[plan]\nagent_tops = 0.5\n")
    with pytest.raises(ValueError, match="unknown keys \\['agent_tops'\\]"):
        load(tmp_path)


# ---------------------------------------------------------------- fixture repos: goldens and acceptance


def normalize(text: str) -> str:
    text = re.sub(r"sherpa \d+\.\d+\.\d+", "sherpa X", text)
    text = re.sub(r"(sherpa: )\d+\.\d+\.\d+", r"\1X", text)
    text = re.sub(r"@[0-9a-f]{10}", "@REV", text)
    return re.sub(r"(rev: )[0-9a-f]{40}", r"\1REV", text)


def check_golden(name: str, text: str) -> None:
    path = GOLDENS / name
    if os.environ.get("SHERPA_UPDATE_GOLDENS"):
        path.write_text(normalize(text), encoding="utf-8", newline="\n")
    assert normalize(text) == path.read_text(encoding="utf-8"), (
        f"golden differs: SHERPA_UPDATE_GOLDENS=1 pytest {__file__}"
    )


def test_poly_fixture_golden(poly_repo: Path):  # noqa: F811
    m = scan(poly_repo, fetch=False)
    p = build_plan(m)
    assert [e.kind for e in p.entries if e.default == PROPOSE] == ["outcome"] + ["owner-doc"] * 13
    assert all(
        set(e.evidence)
        <= {
            "path",
            "files",
            "generated_files",
            "commits_90d",
            "commits_30d",
            "authors_90d",
            "dependents",
            "rank_commits_90d",
            "rank_commits_30d",
            "compared_to",
        }
        for e in p.entries
        if e.kind != "skill"
    )
    check_golden("poly-harness-plan.yaml", yamlio.dumps(p))
    check_golden("poly-console.txt", render_console(p, "harness-plan.yaml"))


@pytest.fixture
def active_repo(tmp_path: Path) -> Path:
    """5 Python modules; ``svc/pay`` with 24 commits by 2 authors and 40 files; Django migrations in ``svc/pay``;
    a test module more active than any business module; ``svc/old`` dormant (only one old commit)."""
    work = tmp_path / "seed"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    files: dict[str, str] = {}
    for name in ("pay", "core", "web", "old"):
        files[f"svc/{name}/pyproject.toml"] = f'[project]\nname = "{name}"\nversion = "0"\n' + (
            'dependencies = ["core"]\n' if name == "pay" else ""
        )
        files[f"svc/{name}/{name}/__init__.py"] = ""
    files["tests/suite/pyproject.toml"] = '[project]\nname = "suite"\nversion = "0"\ndependencies = ["pay", "core"]\n'
    files["tests/suite/test_all.py"] = "def test(): pass\n"
    for i in range(30):
        files[f"svc/pay/pay/mod{i:02d}.py"] = "x = 1\n"
    for i in range(6):
        files[f"svc/pay/pay/migrations/{i:04d}_auto.py"] = "# generated\n"
    files["svc/pay/pay/models.py"] = "class M: pass\n"
    files["svc/pay/manage.py"] = "pass\n"
    commit(work, "init", files, date="2025-06-01T00:00:00Z", author="A")
    for i in range(24):
        commit(
            work,
            f"pay {i}",
            {f"svc/pay/pay/mod{i % 30:02d}.py": f"x = {i}  # pay\n"},
            date=f"2026-02-{(i % 27) + 1:02d}T10:00:00Z",
            author="AB"[i % 2],
        )
    for i in range(26):
        commit(
            work,
            f"tests {i}",
            {"tests/suite/test_all.py": f"def test(): return {i}\n"},
            date=f"2026-02-{(i % 27) + 1:02d}T11:00:00Z",
            author="C",
        )
    commit(work, "core", {"svc/core/core/x.py": "y = 1\n"}, date="2026-02-28T00:00:00Z", author="A")
    commit(work, "web", {"svc/web/web/x.py": "y = 1\n"}, date="2026-03-01T00:00:00Z", author="B")
    origin = tmp_path / "origin.git"
    git(tmp_path, "clone", "-q", "--bare", str(work), str(origin))
    clone = tmp_path / "shop"  # repo name in the plan; the README shows this console view
    git(tmp_path, "clone", "-q", str(origin), str(clone))
    return clone


def test_active_fixture_acceptance(active_repo: Path):
    m = scan(active_repo, fetch=False)
    p = build_plan(m)
    agents = by_kind(p, "agent")
    assert (
        agents["pay"].default == PROPOSE
        and agents["pay"].summary == "rank 1/4 churn ✓ · 24 commits/90d ✓ · 40 files ✓ · 2 authors ✓"
    )
    assert by_kind(p, "owner-doc")["old"].default == SKIP  # dormant: only the old commit
    t = by_kind(p, "test-infra")["suite"]
    assert t.default == PROPOSE and t.summary == "26 commits/90d vs. 24 (pay) ✓"
    s = by_kind(p, "skill")["regenerate-django-migrations"]
    assert s.default == PROPOSE and s.scope == "svc/pay/pay/migrations"
    assert s.evidence["sources"] == ["svc/pay/pay/models.py"] and s.evidence["configs"] == ["svc/pay/manage.py"]
    assert by_kind(p, "librarian")["pay"].default == SKIP  # 24/30d below floor 30, 24/90d below 80
    check_golden("active-console.txt", render_console(p, "harness-plan.yaml"))


# ---------------------------------------------------------------- CLI


def test_cli_plan_scans_when_model_missing_then_reuses_and_keeps_decisions(poly_repo: Path, capsys):  # noqa: F811
    assert main(["plan", str(poly_repo), "--no-fetch"]) == 0
    out, err = capsys.readouterr()
    assert "model scanned" in err and out.startswith("harness-plan.yaml — 14 proposals")
    plan_path = poly_repo / ".sherpa" / "harness-plan.yaml"
    assert plan_path.exists() and (poly_repo / ".sherpa" / "codebase-model.json").exists()
    text = plan_path.read_text(encoding="utf-8").replace("decision: null", "decision: reject", 1)
    plan_path.write_text(text, encoding="utf-8")
    assert main(["plan", str(poly_repo)]) == 0  # no --no-fetch needed: the model exists, no scan
    out, err = capsys.readouterr()
    assert err == "" and "(1 decisions kept)" in out and " [reject]" in out
    assert "decision: reject" in plan_path.read_text(encoding="utf-8")


def test_cli_plan_rescan_and_stdout(poly_repo: Path, capsys):  # noqa: F811
    assert main(["plan", str(poly_repo), "--rescan", "--no-fetch", "--out", "-"]) == 0
    out, err = capsys.readouterr()
    assert out.startswith("# harness-plan") and "model scanned" in err and "harness-plan.yaml — " in err
    assert not (poly_repo / ".sherpa" / "harness-plan.yaml").exists()


def test_cli_plan_stale_model_triggers_rescan(poly_repo: Path, capsys):  # noqa: F811
    mp = poly_repo / ".sherpa" / "codebase-model.json"
    mp.parent.mkdir()
    mp.write_text('{"schema_version": 2}')
    assert main(["plan", str(poly_repo), "--no-fetch"]) == 0
    err = capsys.readouterr().err
    assert "rebuilding the model" in err and "schema_version 2" in err


def test_cli_plan_invalid_decision_is_an_error(poly_repo: Path, capsys):  # noqa: F811
    assert main(["plan", str(poly_repo), "--no-fetch"]) == 0
    pp = poly_repo / ".sherpa" / "harness-plan.yaml"
    pp.write_text(pp.read_text(encoding="utf-8").replace("decision: null", "decision: maybe", 1), encoding="utf-8")
    assert main(["plan", str(poly_repo)]) == 1
    assert "invalid at entries/0/decision: 'maybe' is not one of" in capsys.readouterr().err


def test_cli_plan_outside_git_repo_is_an_error(tmp_path: Path, capsys):
    assert main(["plan", str(tmp_path), "--no-fetch"]) == 1
    assert capsys.readouterr().err.startswith("sherpa plan: ")
