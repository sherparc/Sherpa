"""``sherpa apply`` and ``status``: rendering, ownership modes, write/state/rollback, idempotency, CLI, goldens."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from sherpa import __version__, apply
from sherpa.apply import NEW, SKIPPED, UNCHANGED, UPDATED, Action, plan_files, render_actions, targets_for, write
from sherpa.apply import state as state_mod
from sherpa.apply.render import BLOCKS, JSON_HOOKS, MANAGED, Renderer, Target, entry_key, selected, slug
from sherpa.apply.state import FileRecord, State
from sherpa.check import content_hash
from sherpa.cli import main
from sherpa.plan import PROPOSE, Check, Entry, build_plan
from sherpa.scan import scan
from tests.conftest import commit, git
from tests.test_plan import check_golden, mod, model


def entry(kind, target, scope="", default=PROPOSE, decision=None, **evidence) -> Entry:
    return Entry(kind, target, scope, default, evidence, (Check("x", True),), "cost", None, decision)


# ---------------------------------------------------------------- selection and naming


def test_selected_terraform_model():
    p = build_plan(model([mod("a", "a", c90=5, dependents=("b",)), mod("b", "b", c90=5)]))
    plain = selected(p)
    assert all(e.default == PROPOSE for e in plain)
    entries = [replace(e, decision="reject") if e.target == "a" and e.kind == "owner-doc" else e for e in p.entries]
    entries = [replace(e, decision="accept") if e.kind == "librarian" and e.target == "a" else e for e in entries]
    sel = selected(replace(p, entries=entries))
    assert ("owner-doc", "a") not in {(e.kind, e.target) for e in sel}
    assert ("librarian", "a") in {(e.kind, e.target) for e in sel}


def test_slug_and_entry_key():
    assert slug("Shop.Pricing") == "shop-pricing" and slug("@shop/ui") == "shop-ui" and slug("") == "root"
    assert entry_key(entry("agent", "example.com/shop/lib", "lib")) == "agent:example.com/shop/lib:lib"


def test_slug_collisions_get_the_scope_appended():
    m = model([mod("Shop.Core", "src/Shop.Core", c90=5), mod("shop_core", "lib/shop_core", c90=5)])
    r = Renderer(build_plan(m), m)
    paths = sorted(t.path for t in r.targets() if t.entry and t.entry.startswith("owner-doc") and "/docs/" in t.path)
    assert paths == [
        ".agents/docs/modules/shop-core--lib-shop-core.md",
        ".agents/docs/modules/shop-core--src-shop-core.md",
    ]


# ---------------------------------------------------------------- rendering


def test_targets_are_deterministic_sorted_and_stale_safe():
    m = model([mod("pay", "svc/pay", c90=30, c30=30, authors=2, files=40)])
    p = build_plan(m)
    a, b = targets_for(p, m), targets_for(p, m)
    assert a == b and [t.path for t in a] == sorted(t.path for t in a)
    with pytest.raises(apply.StalePlan, match="run `sherpa plan` first"):
        targets_for(replace(p, model={**p.model, "rev": "0" * 40}), m)
    entries = [replace(e, decision="reject") if e.kind == "outcome" else e for e in p.entries]
    with pytest.raises(ValueError, match="ADR-0008"):
        targets_for(replace(p, entries=entries), m)


def test_rendered_files_follow_the_owner_principle():
    m = model(
        [
            mod("pay", "svc/pay", c90=30, c30=30, authors=2, files=40, deps=("core",), dependents=("web",)),
            mod("core", "svc/core", c90=3),
        ]
    )
    p = build_plan(m)
    by_path = {t.path: t for t in targets_for(p, m)}
    doc = by_path[".agents/docs/modules/pay.md"]
    assert doc.mode == BLOCKS and set(doc.blocks) == {"facts"}
    assert "| depends on | `core` |" in doc.blocks["facts"] and "| dependents | `web` |" in doc.blocks["facts"]
    assert __version__ not in doc.blocks["facts"]  # an upgrade must not rewrite every facts block
    agent = by_path[".claude/agents/pay.md"]
    assert set(agent.blocks) == {"knowledge", "manifest"}
    assert "    - ../.agents/docs/modules/pay.md" in agent.blocks["knowledge"]
    assert "on_demand: []" in agent.blocks["knowledge"]
    assert "[.agents/docs/modules/pay.md](../../.agents/docs/modules/pay.md)" in agent.content
    assert agent.content.startswith("---\nname: pay\ndescription: ")
    base = {t.path: t.mode for t in targets_for(p, m) if t.entry is None}
    assert base == {
        ".agents/scripts/sherpa-check.py": MANAGED,
        ".claude/hooks/sherpa-outcome.py": MANAGED,
        ".claude/settings.json": JSON_HOOKS,
        ".sherpa/telemetry/.gitignore": MANAGED,
        "AGENTS.md": BLOCKS,
        "CLAUDE.md": BLOCKS,
    }
    assert f'SHERPA_VERSION = "{__version__}"' in by_path[".agents/scripts/sherpa-check.py"].content
    assert f'SHERPA_VERSION = "{__version__}"' in by_path[".claude/hooks/sherpa-outcome.py"].content
    assert by_path["CLAUDE.md"].append


def test_claude_md_imports_agents_md_when_present():
    from sherpa.model import FileStat

    m = model([mod("pay", "svc/pay", c90=30, c30=30, authors=2, files=40)])
    only_claude = {t.path: t for t in targets_for(build_plan(m), m, targets=("claude",))}
    assert only_claude["CLAUDE.md"].content.startswith("# Shop\n\n<!-- sherpa:begin harness -->")
    assert "AGENTS.md" not in only_claude and "svc/pay/AGENTS.md" not in only_claude
    assert only_claude["svc/pay/CLAUDE.md"].blocks["harness"].startswith("## pay (managed by sherpa")  # facts inline
    m2 = replace(m, git=replace(m.git, files=[FileStat("AGENTS.md", 10, False, 1, 1, 1, None)]))
    seed = {t.path: t for t in targets_for(build_plan(m2), m2, targets=("claude",))}["CLAUDE.md"].content
    assert seed.startswith("# Shop\n\n@AGENTS.md\n\n<!-- sherpa:begin harness -->")  # existing AGENTS.md is the source
    both = {t.path: t for t in targets_for(build_plan(m), m)}
    assert both["CLAUDE.md"].content.startswith("# Shop\n\n@AGENTS.md\n\n")  # sherpa creates AGENTS.md itself
    assert both["svc/pay/CLAUDE.md"].blocks == {"harness": "@AGENTS.md"} and both["svc/pay/CLAUDE.md"].append
    assert "- `svc/pay/AGENTS.md` — pay" in both["AGENTS.md"].blocks["harness"]
    assert both["svc/pay/AGENTS.md"].blocks["facts"].startswith("## pay (managed by sherpa")


def test_home_claude_keeps_everything_under_claude_and_needs_no_stubs():
    m = model([mod("pay", "svc/pay", c90=30, c30=30, authors=2, files=40, gen=6)])
    from sherpa.model import GeneratorStat

    m = replace(
        m, generators=[GeneratorStat("protobuf", "Protobuf", "pay", "svc/pay/proto", 6, 60, [], [], "protoc", True)]
    )
    paths = {t.path for t in targets_for(build_plan(m), m, home=".claude", targets=("claude",))}
    assert ".claude/docs/modules/pay.md" in paths and ".claude/scripts/sherpa-check.py" in paths
    assert (
        ".claude/skills/regenerate-protobuf/SKILL.md" in paths
        and ".agents/skills/regenerate-protobuf/SKILL.md" not in paths
    )
    agent = {t.path: t for t in targets_for(build_plan(m), m, home=".claude", targets=("claude",))}[
        ".claude/agents/pay.md"
    ]
    assert "    - docs/modules/pay.md" in agent.blocks["knowledge"]


def test_root_module_facts_land_in_the_root_agents_md():
    """A root module's scope is ``""``: its facts land in the root AGENTS.md and the owner-doc link from there
    has no ``../`` — the first real run on a Gradle monorepo rendered ``../.agents/docs/modules/root.md``, C4
    failed and the apply rolled back; no fixture had a root-level manifest."""
    m = model([mod("app", "", c90=30, c30=30, authors=2, files=40)])
    by_path = {t.path: t for t in targets_for(build_plan(m), m, targets=("agents-md",))}
    block = by_path["AGENTS.md"].blocks["harness"]
    assert "## app (managed by sherpa" in block
    assert "](.agents/docs/modules/app.md)" in block and "../" not in block
    assert not any(p.endswith("/AGENTS.md") for p in by_path) and "CLAUDE.md" not in by_path


def test_relpath_from_the_repository_root_and_below():
    from sherpa.apply.render import _relpath

    assert _relpath("", ".agents/docs/modules/app.md") == ".agents/docs/modules/app.md"
    assert _relpath("svc/pay", ".agents/docs/modules/pay.md") == "../../.agents/docs/modules/pay.md"
    assert _relpath(".claude/skills/x", ".agents/skills/x/SKILL.md") == "../../../.agents/skills/x/SKILL.md"


def build_root_repo(tmp_path: Path) -> Path:
    """A repository whose manifest sits at the root (``pyproject.toml``, module ``app``, scope ``""``) next to one
    nested module — the shape of a Gradle or npm monorepo with a root build file."""
    work = tmp_path / "seed"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    files = {"pyproject.toml": '[project]\nname = "app"\nversion = "0"\n', "app/__init__.py": ""}
    for i in range(30):
        files[f"app/mod{i:02d}.py"] = "x = 1\n"
    files["svc/lib/pyproject.toml"] = '[project]\nname = "lib"\nversion = "0"\n'
    for i in range(10):
        files[f"svc/lib/lib/m{i}.py"] = "x = 1\n"
    commit(work, "init", files, date="2025-06-01T00:00:00Z", author="A")
    for i in range(8):
        commit(work, f"app {i}", {f"app/mod{i:02d}.py": f"x = {i}  # app\n"}, date=f"2026-02-{i + 1:02d}T10:00:00Z")
    for i in range(4):
        commit(work, f"lib {i}", {f"svc/lib/lib/m{i}.py": f"x = {i}  # lib\n"}, date=f"2026-02-{i + 1:02d}T11:00:00Z")
    origin = tmp_path / "origin.git"
    git(tmp_path, "clone", "-q", "--bare", str(work), str(origin))
    clone = tmp_path / "mono"
    git(tmp_path, "clone", "-q", str(origin), str(clone))
    return clone


def test_apply_writes_a_repository_with_a_root_module(root_repo: Path, capsys):
    """End to end on the root-manifest fixture: plan → apply writes, the root AGENTS.md links the root module's
    owner doc without a ``../``, the check passes and the second run has nothing to do."""
    applied(root_repo)
    out = capsys.readouterr().out
    assert "check: 0 FAIL" in out and "rolled back" not in out
    root = (root_repo / "AGENTS.md").read_text(encoding="utf-8")
    assert "## app (managed by sherpa" in root and "](.agents/docs/modules/app.md)" in root and "../" not in root
    assert (root_repo / ".agents" / "docs" / "modules" / "app.md").exists()
    assert main(["check", str(root_repo)]) == 0
    assert main(["apply", str(root_repo), "--dry-run"]) == 0
    assert capsys.readouterr().out.endswith("nothing to do.\n")


def test_rollback_takes_the_directories_it_created_with_it(tmp_path: Path):
    """ADR-0032 amended: a rolled-back first apply left empty ``.agents/`` and ``.claude/`` behind, so the next
    run asked which home to use — a dead end caused by the rollback itself. A directory that held the user's
    file before stays."""
    repo = tmp_path
    (repo / ".claude" / "refinements").mkdir(parents=True)
    (repo / ".claude" / "refinements" / "note.md").write_text("mine\n", encoding="utf-8")
    good = Target(".agents/docs/modules/ok.md", MANAGED, None, "# ok\n")
    also = Target(".claude/docs/modules/ok.md", MANAGED, None, "# ok\n")
    bad = Target(".claude/agents/bad.md", MANAGED, None, "<!-- sherpa:begin x -->\nnever closed\n")
    plan = build_plan(model([mod("a", "a", c90=1)]))
    r = write(plan_files([good, also, bad], repo, State()), repo, State(), plan)
    assert r.rolled_back and r.written == 0
    assert not (repo / ".agents").exists()
    assert not (repo / ".claude" / "docs").exists() and not (repo / ".claude" / "agents").exists()
    assert (repo / ".claude" / "refinements" / "note.md").read_text(encoding="utf-8") == "mine\n"


def test_generator_skill_is_linked_from_owner_doc_and_agent():
    from sherpa.model import GeneratorStat

    m = model([mod("pay", "svc/pay", c90=30, c30=30, authors=2, files=40, gen=6)])
    m = replace(
        m,
        generators=[
            GeneratorStat(
                "django-migrations",
                "Django Migrations",
                "pay",
                "svc/pay/pay/migrations",
                6,
                60,
                ["svc/pay/models.py"],
                [],
                "python manage.py makemigrations",
                True,
            )
        ],
    )
    by_path = {t.path: t for t in targets_for(build_plan(m), m)}
    assert (
        "django-migrations → [skill](../../skills/regenerate-django-migrations/SKILL.md)"
        in by_path[".agents/docs/modules/pay.md"].blocks["facts"]
    )
    assert (
        "    - ../.agents/skills/regenerate-django-migrations/SKILL.md"
        in by_path[".claude/agents/pay.md"].blocks["knowledge"]
    )
    skill = by_path[".agents/skills/regenerate-django-migrations/SKILL.md"]
    stub = by_path[".claude/skills/regenerate-django-migrations/SKILL.md"]
    assert stub.mode == MANAGED and "name: regenerate-django-migrations" in stub.content
    assert (
        "[.agents/skills/regenerate-django-migrations/SKILL.md](../../../.agents/skills/regenerate-django-migrations/SKILL.md)"
        in stub.content
    )
    assert "| command | `python manage.py makemigrations` |" in skill.blocks["facts"]


def test_directory_unit_and_accepted_librarian():
    from tests.test_plan import dir_

    m = model(
        [mod("pay", "svc/pay", c90=30, c30=40, authors=2, files=40)], [dir_("infra", files=12, c90=9, c30=1, authors=1)]
    )
    p = build_plan(m)
    entries = [replace(e, decision="accept") if e.kind == "librarian" else e for e in p.entries]
    by_path = {t.path: t for t in targets_for(replace(p, entries=entries), m)}
    infra = by_path[".agents/docs/modules/infra.md"].blocks["facts"]
    assert (
        "| kind | directory without a module manifest |" in infra
        and "| commits 90d / 30d | 9 / 1 · 1 authors |" in infra
    )
    lib = by_path[".agents/skills/pay-sync/SKILL.md"]
    assert (
        lib.blocks == {"scope": lib.blocks["scope"]}
        and "40 commits/30d, suggested cadence: weekly" in lib.blocks["scope"]
    )
    assert "- owner doc: [.agents/docs/modules/pay.md](../../docs/modules/pay.md)" in lib.blocks["scope"]
    assert lib.content.startswith("---\nname: pay-sync\ndescription: ")


def test_coupling_row_and_sub_unit_facts():
    from sherpa.model import Coupling, FileStat
    from tests.test_plan import sub

    subs = [sub("src/app/pay", 3, files=6, c90=12, c30=4, authors=2), sub("src/app/core", 3, files=5, c90=3)]
    m = model(
        [
            mod(
                "app",
                "",
                kind="python",
                files=60,
                c90=30,
                c30=10,
                authors=3,
                sub_dirs=subs,
                coupling=[Coupling("shared-lib", 15, 0.5, 30), Coupling("web", 9, 0.3, 30)],
            ),
        ]
    )
    files = [
        FileStat("src/app/pay/engine.py", 400, False, 9, 3, 2, None),
        FileStat("src/app/pay/models.py", 200, False, 4, 1, 1, None),
        FileStat("src/app/pay/gen.py", 900, True, 9, 1, 1, None),  # generated: never a hotspot
        FileStat("src/app/pay/quiet.py", 900, False, 0, 0, 0, None),  # no commits: never a hotspot
        FileStat("tests/test_pay.py", 100, False, 2, 1, 1, None),
        FileStat("tests/unit/pay_test.py", 50, False, 1, 1, 1, None),
        FileStat("src/app/pay/tests/test_local.py", 10, False, 1, 1, 1, None),  # inside the unit: not "naming it"
        FileStat("tests/goldens/pay-console.txt", 10, False, 1, 1, 1, None),  # a golden: data under tests/, not code
    ]
    m = replace(m, git=replace(m.git, files=files))
    p = build_plan(m)
    by_path = {t.path: t for t in targets_for(p, m)}
    facts = by_path[".agents/docs/modules/app.md"].blocks["facts"]
    assert (
        "| changes together with | `shared-lib` (15 of 30 measured commits, 50 %), `web` (9 of 30 measured commits, 30 %) |"
        in facts
    )  # ADR-0039: the denominator printed is the one share was computed with, not commits_90d
    assert "changes together with" in by_path["AGENTS.md"].blocks["harness"]  # the root proximity block too
    # the root doc knows its sub-units and says where their files are described (one owner per fact)
    assert "| files / LOC | 60 / 600 — 11 files in 2 sub-units, described in their own owner docs |" in facts
    assert (
        "| contains | [src/app/core](src-app-core.md) (5 files, 3 commits/90d), "
        "[src/app/pay](src-app-pay.md) (6 files, 12 commits/90d) |" in facts
    )
    pay = by_path[".agents/docs/modules/src-app-pay.md"].blocks["facts"]
    assert "| kind | directory inside module `app` (package) |" in pay
    assert "| files / LOC | 6 / 60 (6 source files) |" in pay and "| commits 90d / 30d | 12 / 4 · 2 authors |" in pay
    assert "| hotspots | `src/app/pay/engine.py`, `src/app/pay/models.py`, `src/app/pay/tests/test_local.py` |" in pay
    assert "| tests naming it | `tests/test_pay.py`, `tests/unit/pay_test.py` |" in pay
    core = by_path[".agents/docs/modules/src-app-core.md"].blocks["facts"]
    assert "| hotspots | — |" in core and "| tests naming it | none — a name match, not a dependency |" in core
    nested = by_path["src/app/pay/AGENTS.md"].blocks["facts"]
    assert "| part of | `app` — 6 files, 12 commits/90d |" in nested
    assert (
        "| hotspots | `src/app/pay/engine.py`, `src/app/pay/models.py`, `src/app/pay/tests/test_local.py` |" in nested
    )
    assert "changes together with" not in nested  # coupling is measured per module, not per sub-unit


def test_root_index_is_capped_and_ordered_by_rank():
    from sherpa.apply.render import INDEX_MAX

    mods = [mod(f"m{i:02d}", f"svc/m{i:02d}", c90=i + 1, files=10) for i in range(INDEX_MAX + 6)]
    m = model(mods)
    p = build_plan(m)
    root = {t.path: t for t in targets_for(p, m)}["AGENTS.md"].blocks["harness"]
    lines = [ln for ln in root.splitlines() if ln.startswith("- `svc/")]
    assert len(lines) == INDEX_MAX and lines[0] == "- `svc/m25/AGENTS.md` — m25" and lines[-1].endswith("m06")
    assert "- … and 6 more, each with its own AGENTS.md; every unit is listed in `.agents/docs/modules/`" in root
    assert "most active first" in root


# ---------------------------------------------------------------- plan_files: ownership modes


def managed(content="v2\n") -> Target:
    return Target("x/f.py", MANAGED, None, content)


def blocks(inner="new facts", append=False) -> Target:
    seed = f"# title\n\n<!-- sherpa:begin facts -->\n{inner}\n<!-- sherpa:end facts -->\n\n## human\n"
    return Target("d/doc.md", BLOCKS, "owner-doc:d:d", seed, {"facts": inner}, append=append)


def run(target: Target, tmp_path: Path, current: str | None, rec: FileRecord | None) -> Action:
    p = tmp_path / target.path
    if current is not None:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(current, encoding="utf-8", newline="\n")
    state = State(files={target.path: rec} if rec else {})
    (a,) = plan_files([target], tmp_path, state)
    return a


def test_managed_file_modes(tmp_path: Path):
    t = managed()
    assert (a := run(t, tmp_path, None, None)).op == NEW and a.new == "v2\n" and a.record.hash == content_hash("v2\n")
    a = run(t, tmp_path, "theirs\n", None)
    assert a.op == SKIPPED and "sherpa adopt" in a.detail and a.new is None and a.record is None
    a = run(t, tmp_path, "edited\n", FileRecord(MANAGED, hash=content_hash("v1\n")))
    assert (a.op, a.detail) == (SKIPPED, "hand-edited (skipped)")
    a = run(t, tmp_path, "v1\n", FileRecord(MANAGED, hash=content_hash("v1\n")))
    assert a.op == UPDATED and a.new == "v2\n" and a.old == "v1\n"
    a = run(t, tmp_path, "v2\r\n", FileRecord(MANAGED, hash=content_hash("v2\n")))
    assert a.op == UNCHANGED and a.new is None  # CRLF checkout is not a hand edit


def test_blocks_file_modes(tmp_path: Path):
    t = blocks("new facts")
    old_rec = FileRecord(BLOCKS, blocks={"facts": content_hash("old facts")})
    assert run(t, tmp_path, None, None).op == NEW
    # human text outside the block survives, the block is regenerated
    cur = "# title\n\n<!-- sherpa:begin facts -->\nold facts\n<!-- sherpa:end facts -->\n\n## human\n\nMy notes.\n"
    a = run(t, tmp_path, cur, old_rec)
    assert (a.op, a.detail) == (UPDATED, "block facts updated")
    assert (
        a.new
        == "# title\n\n<!-- sherpa:begin facts -->\nnew facts\n<!-- sherpa:end facts -->\n\n## human\n\nMy notes.\n"
    )
    assert a.record.blocks == {"facts": content_hash("new facts")}
    # a hand edit inside the block is respected
    a = run(t, tmp_path, cur.replace("old facts", "my facts"), old_rec)
    assert (a.op, a.detail) == (SKIPPED, "block facts hand-edited (skipped)")
    # markers removed by hand
    a = run(t, tmp_path, "# title\n\n## human\n", old_rec)
    assert (a.op, a.detail) == (SKIPPED, "block facts removed by hand (skipped)") and a.record.blocks == {}
    # broken markers
    a = run(t, tmp_path, "<!-- sherpa:begin facts -->\nx\n", old_rec)
    assert a.op == SKIPPED and "markers broken" in a.detail
    # exists without markers and without state → not ours
    a = run(t, tmp_path, "# theirs\n", None)
    assert a.op == SKIPPED and "sherpa adopt" in a.detail
    # markers present but no state record → somebody's block, never overwritten (ADR-0016)
    a = run(t, tmp_path, cur, None)
    assert (a.op, a.detail) == (SKIPPED, "exists with sherpa markers but no state record — `sherpa adopt`")
    # a block with sherpa's name that sherpa never wrote (no hash in the record) stays untouched
    a = run(t, tmp_path, cur, FileRecord(BLOCKS, blocks={}))
    assert (a.op, a.detail) == (SKIPPED, "block facts not written by sherpa (skipped)")
    # unchanged
    a = run(
        t,
        tmp_path,
        cur.replace("old facts", "new facts"),
        FileRecord(BLOCKS, blocks={"facts": content_hash("new facts")}),
    )
    assert a.op == UNCHANGED


def test_blocks_append_for_claude_md(tmp_path: Path):
    t = blocks("harness text", append=True)
    a = run(t, tmp_path, "# Their CLAUDE.md\n\nRules.", None)
    assert (a.op, a.detail) == (UPDATED, "block facts appended")
    assert (
        a.new == "# Their CLAUDE.md\n\nRules.\n\n<!-- sherpa:begin facts -->\nharness text\n<!-- sherpa:end facts -->\n"
    )


def test_two_blocks_one_hand_edited(tmp_path: Path):
    t = Target("a.md", BLOCKS, None, "", {"k": "k2", "m": "m2"})
    cur = "<!-- sherpa:begin k -->\nk1\n<!-- sherpa:end k -->\nmid\n<!-- sherpa:begin m -->\nmine\n<!-- sherpa:end m -->\n"
    a = run(t, tmp_path, cur, FileRecord(BLOCKS, blocks={"k": content_hash("k1"), "m": content_hash("m1")}))
    assert (a.op, a.detail) == (UPDATED, "block k updated; block m hand-edited")
    assert (
        a.new
        == "<!-- sherpa:begin k -->\nk2\n<!-- sherpa:end k -->\nmid\n<!-- sherpa:begin m -->\nmine\n<!-- sherpa:end m -->\n"
    )
    assert a.record.blocks == {"k": content_hash("k2"), "m": content_hash("m1")}


def test_hooks_merge_keeps_foreign_entries(tmp_path: Path):
    hooks = {"Stop": [{"hooks": [{"type": "command", "command": "python3 x/sherpa-outcome.py"}]}]}
    t = Target(".claude/settings.json", JSON_HOOKS, None, hooks=hooks)
    a = run(t, tmp_path, None, None)
    assert a.op == NEW and json.loads(a.new) == {"hooks": hooks}
    theirs = {
        "permissions": {"allow": ["Bash"]},
        "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "their.sh"}]}], "PreToolUse": []},
    }
    a = run(t, tmp_path, json.dumps(theirs), None)
    assert (a.op, a.detail) == (UPDATED, "hooks added: Stop")
    merged = json.loads(a.new)
    assert merged["permissions"] == theirs["permissions"] and merged["hooks"]["PreToolUse"] == []
    assert [h["hooks"][0]["command"] for h in merged["hooks"]["Stop"]] == ["their.sh", "python3 x/sherpa-outcome.py"]
    a = run(t, tmp_path, a.new, None)
    assert (a.op, a.detail) == (UNCHANGED, "hooks present")
    a = run(t, tmp_path, "{oops", None)
    assert a.op == SKIPPED and "not valid JSON" in a.detail
    a = run(t, tmp_path, "[]", None)
    assert a.op == SKIPPED and "not an object" in a.detail
    # somebody's shape — a template with ``"hooks": []``, an event that is a string, a group that is a string —
    # is skipped with a line, never a traceback in the preview (plan §14 F60)
    for theirs in ('{"hooks": []}', '{"hooks": {"Stop": "nope"}}', '{"hooks": {"Stop": "x", "PreToolUse": []}}'):
        a = run(t, tmp_path, theirs, None)
        assert (a.op, a.detail) == (SKIPPED, "hooks is not an object of event lists — yours (skipped)"), theirs
    a = run(t, tmp_path, '{"hooks": {"Stop": ["str", {"hooks": "x"}, {"hooks": [1]}]}}', None)
    assert (a.op, a.detail) == (UPDATED, "hooks added: Stop") and len(json.loads(a.new)["hooks"]["Stop"]) == 4


# ---------------------------------------------------------------- write, state, rollback


def tree_hash(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(x for x in root.rglob("*") if x.is_file() and ".git" not in x.parts and "telemetry" not in x.parts):
        h.update(p.relative_to(root).as_posix().encode())
        h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def applied(repo: Path) -> None:
    assert main(["plan", str(repo), "--no-fetch"]) == 0
    assert main(["apply", str(repo), "--yes"]) == 0


def test_apply_and_check_treat_foreign_findings_as_hints(active_repo: Path, capsys):
    """ADR-0047: a dead link in a file sherpa never wrote is a WARN `(yours)` — apply writes, `check` exits
    0, `--strict` exits 1; a dead link in sherpa's own rendering would still roll back."""
    (active_repo / ".claude" / "refinements").mkdir(parents=True)
    (active_repo / ".claude" / "refinements" / "note.md").write_text("[x](../nowhere.md)\n", encoding="utf-8")
    applied(active_repo)
    out = capsys.readouterr().out
    assert "check: 0 FAIL, 1 WARN" in out and "C4" not in out  # apply lists FAILs only
    assert main(["check", str(active_repo)]) == 0
    assert "WARN C4 .claude/refinements/note.md: link target ../nowhere.md does not exist (yours)\n" in (
        capsys.readouterr().out
    )
    assert main(["check", str(active_repo), "--strict"]) == 1
    assert "FAIL C4 .claude/refinements/note.md: link target ../nowhere.md does not exist\n" in capsys.readouterr().out
    assert main(["status", str(active_repo)]) == 0
    assert "check: 0 FAIL, 1 WARN" in capsys.readouterr().out


def test_apply_is_idempotent_and_deterministic(active_repo: Path, capsys):
    applied(active_repo)
    out = capsys.readouterr().out
    assert "18 to add, 0 to change, 0 unchanged, 0 skipped." in out and "check: 0 FAIL, 0 WARN" in out
    state_path = active_repo / ".sherpa" / "state.json"
    first = state_path.read_bytes()
    st = state_mod.load(state_path)
    state_mod.validate(json.loads(first))
    assert (
        st.sherpa == __version__
        and len(st.harness_rev) == 12
        and len(st.files) == 18
        and st.home == ".agents"
        and st.targets == ("claude", "agents-md")
    )
    assert st.plan["rev"] == scan(active_repo, fetch=False).git.trunk.rev
    h1 = tree_hash(active_repo / ".claude")
    assert main(["apply", str(active_repo), "--yes"]) == 0
    out = capsys.readouterr().out
    assert "0 to add, 0 to change, 18 unchanged, 0 skipped.\nnothing to do.\n" in out
    assert state_path.read_bytes() == first and tree_hash(active_repo / ".claude") == h1
    # the same input on a second clone → byte-identical tree
    r = subprocess.run(
        ["git", "check-ignore", ".sherpa/telemetry/outcomes.ndjson"], cwd=active_repo, capture_output=True, text=True
    )
    assert r.returncode == 0  # telemetry never enters the repo


def test_harness_rev_changes_only_with_content_and_tooling_with_the_version():
    """ADR-0056: ``harness_rev`` is over what an agent reads; the checker copy, the hook and the version move
    ``tooling`` only — a ``self-update`` plus ``apply`` keeps the revision the outcome labels are grouped by."""
    files = {
        "a.md": FileRecord(MANAGED, hash="a" * 16),
        "AGENTS.md": FileRecord(BLOCKS, blocks={"x": "b" * 16}),
        ".agents/scripts/sherpa-check.py": FileRecord(MANAGED, hash="c" * 16),
        ".claude/settings.json": FileRecord(JSON_HOOKS, hash="d" * 16),
    }
    rev, tooling = state_mod.harness_rev(files), state_mod.tooling_rev(files)
    assert rev == state_mod.harness_rev(dict(reversed(list(files.items()))))
    assert rev != state_mod.harness_rev({**files, "AGENTS.md": FileRecord(BLOCKS, blocks={"x": "c" * 16})})
    new_checker = {**files, ".agents/scripts/sherpa-check.py": FileRecord(MANAGED, hash="e" * 16)}
    assert state_mod.harness_rev(new_checker) == rev and state_mod.tooling_rev(new_checker) != tooling
    assert state_mod.tooling_rev(files, version="9.9.9") != tooling
    assert state_mod.harness_rev({}) == state_mod.harness_rev({".claude/hooks/sherpa-outcome.py": FileRecord(MANAGED)})


def test_trunk_move_without_activity_changes_no_block(active_repo: Path, capsys):
    """ADR-0019: a merge that touches nothing a unit measures moves the rev, not the numbers — apply says
    ``nothing to do.`` instead of rewriting every block with a new stamp."""
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    assert main(["apply", str(active_repo), "--yes"]) == 0
    seed = active_repo.parent / "seed"
    commit(seed, "docs only", {"README.md": "# shop\n"}, date="2026-03-01T12:00:00Z", author="A")  # same window end
    subprocess.run(["git", "push", "-q", str(active_repo.parent / "origin.git"), "main"], cwd=seed, check=True)
    subprocess.run(["git", "fetch", "-q", "origin"], cwd=active_repo, check=True)
    capsys.readouterr()
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "nothing to do." in out and "~" not in out.split("\n", 2)[2]


def test_status_reports_a_stale_plan_and_json(active_repo: Path, capsys):
    """The daily command says what ``apply`` would refuse: the trunk moved since the plan was made. Same report
    as JSON for scripts — a stale plan is a warning, never an exit code."""
    applied(active_repo)
    capsys.readouterr()
    assert main(["status", str(active_repo)]) == 0
    assert "\nplan: current\n" in capsys.readouterr().out
    seed = active_repo.parent / "seed"
    commit(seed, "docs only", {"README.md": "# shop\n"}, date="2026-03-01T12:00:00Z", author="A")
    subprocess.run(["git", "push", "-q", str(active_repo.parent / "origin.git"), "main"], cwd=seed, check=True)
    subprocess.run(["git", "fetch", "-q", "origin"], cwd=active_repo, check=True)
    assert main(["status", str(active_repo)]) == 0
    out = capsys.readouterr().out
    assert "\nplan: stale — origin/main moved " in out and "since `sherpa plan`; run `sherpa plan`\n" in out
    assert "drift: none" in out  # the harness itself is current (ADR-0019) — the two facts are separate lines
    assert main(["status", str(active_repo), "--json"]) == 0
    j = json.loads(capsys.readouterr().out)
    assert j["plan"]["stale"] is True and j["plan"]["trunk"] == "origin/main" and len(j["plan"]["current_rev"]) == 40
    assert j["plan"]["plan_rev"] != j["plan"]["current_rev"]
    assert j["drift"] == [] and j["findings"] == [] and j["outcomes"] == {} and len(j["harness_rev"]) == 12
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0  # re-plan: current again
    capsys.readouterr()
    assert main(["status", str(active_repo), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["plan"] == {"stale": False}


def test_status_names_adopt_on_a_foreign_state_schema(active_repo: Path, capsys):
    """ADR-0017: a state from another schema version is unreadable, and the message names the way out; the
    report itself still comes (ADR-0034), computed against an empty index."""
    applied(active_repo)
    path = active_repo / ".sherpa" / "state.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    d["schema_version"] = 2
    path.write_text(json.dumps(d), encoding="utf-8")
    capsys.readouterr()
    assert main(["status", str(active_repo)]) == 0
    out, err = capsys.readouterr()
    assert "\nstate: unreadable — " in out and "\ndrift: unknown until the state is rebuilt\n" in out
    assert "  + " not in out, "no drift lines against an empty index"
    assert main(["status", str(active_repo), "--json"]) == 0
    j = json.loads(capsys.readouterr().out)
    assert "schema_version 2, expected 1" in j["state"]["error"] and j["drift"] == []
    assert "state has schema_version 2, expected 1" in err and "`sherpa adopt` rebuilds it" in err


def test_a_gone_file_the_plan_no_longer_wants_loses_its_record(active_repo: Path, capsys):
    """Reject an entry, delete its file by hand: status names it, apply drops the record (ADR-0048)."""
    applied(active_repo)
    assert main(["plan", str(active_repo), "--no-fetch", "--reject", "agent:pay"]) == 0
    (active_repo / ".claude" / "agents" / "pay.md").unlink()
    capsys.readouterr()
    assert main(["status", str(active_repo)]) == 0
    assert "  - .claude/agents/pay.md  in the state, not on disk — `apply` drops the record" in capsys.readouterr().out
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "  - .claude/agents/pay.md" in out and "already gone — record dropped" in out and "1 to remove." in out
    assert main(["apply", str(active_repo), "--yes"]) == 0
    assert "0 files written · harness_rev" in capsys.readouterr().out
    assert ".claude/agents/pay.md" not in state_mod.load(active_repo / state_mod.STATE_PATH).files
    assert main(["status", str(active_repo)]) == 0
    assert "drift: none" in capsys.readouterr().out


def test_rescan_updates_the_facts_block_and_keeps_human_text(active_repo: Path, capsys):
    applied(active_repo)
    doc = active_repo / ".agents" / "docs" / "modules" / "pay.md"
    doc.write_text(
        doc.read_text(encoding="utf-8").replace("## structure\n", "## structure\n\nOrder → charge → ledger.\n"),
        encoding="utf-8",
    )
    # human edits another agent's block by hand — that block is theirs now
    agent = active_repo / ".claude" / "agents" / "pay.md"
    agent.write_text(agent.read_text(encoding="utf-8").replace("Read first:", "Read FIRST:"), encoding="utf-8")
    seed = active_repo.parent / "seed"
    commit(seed, "more pay", {"svc/pay/pay/new.py": "z = 1\n"}, date="2026-03-02T00:00:00Z", author="A")
    subprocess.run(["git", "push", "-q", str(active_repo.parent / "origin.git"), "main"], cwd=seed, check=True)
    subprocess.run(["git", "fetch", "-q", "origin"], cwd=active_repo, check=True)
    assert main(["apply", str(active_repo), "--dry-run"]) == 1  # the trunk moved: a saved plan is stale
    err = capsys.readouterr().err
    assert "is now at" in err and "run `sherpa plan` first" in err
    assert main(["plan", str(active_repo)]) == 0
    assert main(["apply", str(active_repo), "--yes"]) == 0
    out = capsys.readouterr().out
    assert "~ .agents/docs/modules/pay.md" in out and "block facts updated" in out
    assert "~ svc/pay/AGENTS.md" in out  # the proximity file follows the facts
    assert "! .claude/agents/pay.md" in out and "block manifest hand-edited (skipped)" in out
    text = doc.read_text(encoding="utf-8")
    assert "Order → charge → ledger." in text and "| files / LOC | 41 / 43 (6 generated) |" in text
    assert "Read FIRST:" in agent.read_text(encoding="utf-8")


def test_write_rolls_back_when_it_introduces_a_fail(tmp_path: Path, capsys):
    repo = tmp_path
    (repo / ".claude" / "agents").mkdir(parents=True)
    (repo / ".claude" / "agents" / "theirs.md").write_text("no front matter\n", encoding="utf-8")  # pre-existing FAIL
    good = Target(".claude/docs/modules/ok.md", MANAGED, None, "# ok\n")
    bad = Target(".claude/docs/modules/bad.md", MANAGED, None, "<!-- sherpa:begin x -->\nnever closed\n")
    plan = build_plan(model([mod("a", "a", c90=1)]))
    actions = plan_files([good], repo, State())
    r = write(actions, repo, State(), plan)
    assert not r.rolled_back and r.written == 1 and (repo / ".claude/docs/modules/ok.md").exists()
    assert r.state.files[".claude/docs/modules/ok.md"].mode == MANAGED and (repo / ".sherpa/state.json").exists()
    before = (repo / ".sherpa/state.json").read_bytes()
    actions = plan_files([good, bad], repo, r.state)
    r2 = write(actions, repo, r.state, plan)
    assert r2.rolled_back and r2.written == 0 and not (repo / ".claude/docs/modules/bad.md").exists()
    assert (repo / ".sherpa/state.json").read_bytes() == before
    assert [f.rule for f in r2.findings] == ["C5"]
    assert apply.render_result(r2).startswith("check: 1 new FAIL — rolled back, nothing written\n  FAIL C5")


def test_write_without_check(tmp_path: Path):
    bad = Target("CLAUDE.md", MANAGED, None, "<!-- sherpa:begin x -->\n")
    plan = build_plan(model([mod("a", "a", c90=1)]))
    r = write(plan_files([bad], tmp_path, State()), tmp_path, State(), plan, check=False)
    assert r.written == 1 and not r.rolled_back and r.findings == []


def test_state_round_trip_and_schema_guard(tmp_path: Path):
    st = State(
        "a" * 12,
        {"trunk": "origin/main"},
        "2026-01-01T00:00:00Z",
        {"f": FileRecord(BLOCKS, entry="k:t:s", blocks={"b": "0" * 16})},
    )
    st.write(tmp_path / "s.json")
    assert state_mod.load(tmp_path / "s.json") == st
    with pytest.raises(ValueError, match="schema_version"):
        State.from_dict({"schema_version": 0, "sherpa": "x"})


# ---------------------------------------------------------------- status


def test_status_reports_drift_orphans_outcomes_and_version(active_repo: Path, capsys):
    applied(active_repo)
    capsys.readouterr()
    assert main(["status", str(active_repo)]) == 0
    out = capsys.readouterr().out
    assert "drift: none — files match the state and the plan\ncheck: 0 FAIL, 0 WARN\noutcomes: none yet" in out
    hook = active_repo / ".claude" / "hooks" / "sherpa-outcome.py"
    hook.write_text(hook.read_text(encoding="utf-8") + "# mine\n", encoding="utf-8")
    (active_repo / ".agents" / "docs" / "modules" / "core.md").unlink()
    st = state_mod.load(active_repo / ".sherpa" / "state.json")
    st.files[".claude/agents/old.md"] = FileRecord(BLOCKS, entry="agent:old:svc/old", blocks={})
    (active_repo / ".claude" / "agents" / "old.md").write_text(
        "---\nname: old\ndescription: d\n---\n", encoding="utf-8"
    )
    st.write(active_repo / ".sherpa" / "state.json")
    tele = active_repo / ".sherpa" / "telemetry"
    tele.mkdir(exist_ok=True)
    (tele / "outcomes.ndjson").write_text(
        "\n".join(
            [
                json.dumps({"kind": "outcome", "harness_rev": st.harness_rev, "label": "success"}),
                json.dumps({"kind": "outcome", "harness_rev": st.harness_rev, "label": "unknown"}),
                json.dumps({"kind": "outcome", "harness_rev": "000000000000", "label": "failed", "ts": 5}),
                json.dumps({"kind": "correction", "harness_rev": st.harness_rev}),
                "not json",
                # seven older revisions, first seen at ts 10 … 70: newest first, five shown, the rest counted (F65)
                *(
                    json.dumps({"kind": "outcome", "harness_rev": f"{i:012d}", "label": "success", "ts": i * 10})
                    for i in range(1, 8)
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    check_py = active_repo / ".agents" / "scripts" / "sherpa-check.py"
    check_py.write_text(
        check_py.read_text(encoding="utf-8").replace(f'SHERPA_VERSION = "{__version__}"', 'SHERPA_VERSION = "0.0.1"'),
        encoding="utf-8",
    )
    assert main(["status", str(active_repo)]) == 1  # the deleted owner doc breaks the nested AGENTS.md link
    out = capsys.readouterr().out
    assert (
        "drift: 4 files" in out and "FAIL C4 svc/core/AGENTS.md: link target ../../.agents/docs/modules/core.md" in out
    )
    assert (
        "  ? .claude/agents/old.md            no longer in the plan, changed by hand — `apply` drops the record, the file is yours"
        in out
    )
    assert "  - .agents/docs/modules/core.md     in the state, not on disk — apply recreates it" in out
    assert "  ! .claude/hooks/sherpa-outcome.py  hand-edited (skipped)" in out
    assert "  ! .agents/scripts/sherpa-check.py  hand-edited (skipped)" in out
    assert "outcomes: 10 executions labelled, 1 corrections\n" in out
    older = "".join(f"  {i:012d}: 1 success, 0 failed, 0 unknown\n" for i in (7, 6, 5, 4, 3))
    assert (
        f"  {st.harness_rev} (current): 1 success, 0 failed, 1 unknown\n{older}"
        "  and 3 older revisions — `sherpa status --json` lists them all\n"
    ) in out
    assert f"note: .agents/scripts/sherpa-check.py is sherpa 0.0.1, installed is {__version__}" in out
    (active_repo / "CLAUDE.md").write_text("<!-- sherpa:begin harness -->\n", encoding="utf-8")
    assert main(["status", str(active_repo)]) == 1  # a FAIL is the only non-zero exit of status
    assert "FAIL C5 CLAUDE.md" in capsys.readouterr().out


# ---------------------------------------------------------------- CLI


def test_cli_apply_needs_plan_and_model(tmp_path: Path, capsys):
    assert main(["apply", str(tmp_path)]) == 1
    assert "harness-plan.yaml not found — run `sherpa plan` first" in capsys.readouterr().err
    (tmp_path / ".sherpa").mkdir()
    (tmp_path / ".sherpa" / "harness-plan.yaml").write_text("{}", encoding="utf-8")
    assert main(["status", str(tmp_path)]) == 1
    assert "codebase-model.json not found" in capsys.readouterr().err


def test_cli_apply_dry_run_asks_and_aborts(active_repo: Path, capsys, monkeypatch):
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    capsys.readouterr()
    assert main(["apply", str(active_repo)]) == 0  # no terminal → dry run only
    assert "dry run only — pass --yes to write (no terminal to ask)." in capsys.readouterr().out
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    assert "18 to add" in capsys.readouterr().out and not (active_repo / "CLAUDE.md").exists()
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert main(["apply", str(active_repo)]) == 0
    assert "aborted, nothing written." in capsys.readouterr().out and not (active_repo / "CLAUDE.md").exists()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert main(["apply", str(active_repo)]) == 0
    assert "18 files written" in capsys.readouterr().out and (active_repo / "CLAUDE.md").exists()


def test_cli_apply_treats_eof_on_the_question_as_no_terminal(active_repo: Path, capsys, monkeypatch):
    """Plan §13 F57, found by the e2e theses on Windows CI: a redirected ``NUL`` passes ``isatty()`` there, so
    ``apply`` without ``--yes`` asked and died with ``EOFError`` — exit 1 and a traceback in a CI job. EOF on
    a question is no terminal: the dry run's closing line, exit 0, nothing written; the home question refuses
    with the fix named when both homes exist and takes the default when none does."""
    from sherpa.cli import _resolve_layout

    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    capsys.readouterr()
    stdin = io.StringIO()  # empty: the first read is EOF — the prompt has been printed by then
    stdin.isatty = lambda: True  # type: ignore[method-assign]
    monkeypatch.setattr(sys, "stdin", stdin)
    assert main(["apply", str(active_repo)]) == 0
    out, err = capsys.readouterr()
    assert out.endswith("apply? [y/N] \ndry run only — pass --yes to write (no terminal to ask).\n") and err == ""
    assert not (active_repo / "CLAUDE.md").exists() and not (active_repo / ".agents").exists()
    assert _resolve_layout(active_repo, State(), ask=True)[0] == ".agents"  # no home yet: the default
    (active_repo / ".agents").mkdir()
    (active_repo / ".claude").mkdir()
    with pytest.raises(ValueError, match="both .agents/ and .claude/ exist — .*sherpa.toml"):
        _resolve_layout(active_repo, State(), ask=True)


def test_cli_check(active_repo: Path, capsys):
    applied(active_repo)
    capsys.readouterr()
    assert main(["check", str(active_repo)]) == 0
    assert capsys.readouterr().out.startswith(f"sherpa check {active_repo.resolve()}: 0 FAIL, 0 WARN\n")
    assert main(["check", str(active_repo), "--json"]) == 0 and capsys.readouterr().out == "[]\n"


# ---------------------------------------------------------------- goldens (the README shows these)


def test_active_fixture_goldens(active_repo: Path, capsys):
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    capsys.readouterr()
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    check_golden("active-apply-console.txt", capsys.readouterr().out)
    assert main(["apply", str(active_repo), "--yes"]) == 0
    check_golden("active-owner-doc-pay.md", (active_repo / ".agents/docs/modules/pay.md").read_text(encoding="utf-8"))
    check_golden("active-agents-md-root.md", (active_repo / "AGENTS.md").read_text(encoding="utf-8"))
    check_golden("active-agents-md-pay.md", (active_repo / "svc/pay/AGENTS.md").read_text(encoding="utf-8"))
    check_golden("active-agent-pay.md", (active_repo / ".claude/agents/pay.md").read_text(encoding="utf-8"))
    check_golden(
        "active-skill-migrations.md",
        (active_repo / ".agents/skills/regenerate-django-migrations/SKILL.md").read_text(encoding="utf-8"),
    )
    check_golden("active-claude-md.md", (active_repo / "CLAUDE.md").read_text(encoding="utf-8"))


def test_render_actions_columns():
    t = Target(".claude/agents/x.md", BLOCKS, "agent:example.com/x:x", "")
    plan = build_plan(model([mod("a", "a", c90=1)]))
    out = render_actions([Action(t, NEW, "new", "", None, None)], plan)
    assert "  + .claude/agents/x.md  agent example.com/x           new\n" in out
    assert out.endswith("1 to add, 0 to change, 0 unchanged, 0 skipped.\n")


# ---------------------------------------------------------------- the outcome hook (subprocess, as Claude Code runs it)


HOOK = Path(apply.__file__).parent / "assets" / "sherpa-outcome.py"


def fire(repo: Path, event: dict) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(repo)}
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event), capture_output=True, text=True, env=env)


def labels(repo: Path) -> list[dict]:
    p = repo / ".sherpa" / "telemetry" / "outcomes.ndjson"
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


def test_outcome_hook_labels_executions(tmp_path: Path):
    (tmp_path / ".sherpa").mkdir()
    (tmp_path / ".sherpa" / "state.json").write_text(json.dumps({"harness_rev": "abc123abc123"}), encoding="utf-8")
    s = "s1"
    events = [
        {"hook_event_name": "UserPromptSubmit", "session_id": s, "prompt": "add a test"},
        {"hook_event_name": "PostToolUse", "session_id": s, "tool_name": "Edit", "tool_input": {}},
        {
            "hook_event_name": "PostToolUse",
            "session_id": s,
            "tool_name": "Bash",
            "tool_input": {"command": "pytest -q tests"},
        },
        {"hook_event_name": "Stop", "session_id": s},
        {"hook_event_name": "UserPromptSubmit", "session_id": s, "prompt": "No, that's wrong — the test fails"},
        {
            "hook_event_name": "PostToolUseFailure",
            "session_id": s,
            "tool_name": "Bash",
            "tool_input": {"command": "dotnet test"},
        },
        {"hook_event_name": "Stop", "session_id": s},
        {"hook_event_name": "UserPromptSubmit", "session_id": s, "prompt": "what does pay do?"},
        {"hook_event_name": "Stop", "session_id": s},
        {"hook_event_name": "UserPromptSubmit", "session_id": s, "prompt": "open a PR"},
        {
            "hook_event_name": "PostToolUse",
            "session_id": s,
            "tool_name": "Bash",
            "tool_input": {"command": "git push && gh pr create -f"},
        },
        {"hook_event_name": "Stop", "session_id": s},
        {"hook_event_name": "Stop", "session_id": s},  # a second Stop without a prompt: nothing to label
    ]
    for ev in events:
        r = fire(tmp_path, ev)
        assert r.returncode == 0 and r.stdout == "" and r.stderr == ""
    recs = labels(tmp_path)
    assert [(r["kind"], r.get("label")) for r in recs] == [
        ("outcome", "success"),
        ("correction", "failed"),
        ("outcome", "failed"),
        ("outcome", "unknown"),
        ("outcome", "success"),
    ]
    first = recs[0]
    assert first["id"] == "s1:1" and first["harness_rev"] == "abc123abc123" and first["sherpa"] == "dev"
    assert first["signals"] == {
        "bash": 1,
        "bash_errors": 0,
        "edits": 1,
        "tests_run": 1,
        "tests_failed": 0,
        "last_test": "green",
        "pushed": False,
        "pr_created": False,
    }
    assert recs[1]["execution"] == "s1:1"
    assert recs[2]["signals"]["tests_failed"] == 1 and recs[4]["signals"] == {
        **first["signals"],
        "edits": 0,
        "tests_run": 0,
        "last_test": None,
        "pushed": True,
        "pr_created": True,
    }


def test_outcome_hook_fails_open(tmp_path: Path):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
    r = subprocess.run([sys.executable, str(HOOK)], input="not json", capture_output=True, text=True, env=env)
    assert r.returncode == 0 and r.stdout == "" and r.stderr == ""
    r = fire(
        tmp_path,
        {"hook_event_name": "PostToolUse", "session_id": "x", "tool_name": "Bash", "tool_input": {"command": "pytest"}},
    )
    assert r.returncode == 0 and labels(tmp_path) == []  # no open execution → nothing recorded
    r = fire(tmp_path, {"hook_event_name": "Stop", "session_id": "x"})
    assert r.returncode == 0 and labels(tmp_path) == []
    r = fire(tmp_path, {"hook_event_name": "UserPromptSubmit", "prompt": "hi"})  # no session id, no state.json
    assert r.returncode == 0
    r = fire(tmp_path, {"hook_event_name": "Stop"})
    assert labels(tmp_path)[0]["harness_rev"] == "none" and labels(tmp_path)[0]["session_id"] == "unknown"


# ---------------------------------------------------------------- target layer (ADR-0015): home and targets


def test_config_apply_section(tmp_path: Path):
    from sherpa.config import load

    (tmp_path / "sherpa.toml").write_text('[apply]\nhome = ".claude"\ntargets = ["agents-md"]\n', encoding="utf-8")
    assert (load(tmp_path).apply.home, load(tmp_path).apply.targets) == (".claude", ("agents-md",))
    for bad, msg in (
        ('[apply]\nhome = "docs"\n', "home 'docs' — allowed"),
        ('[apply]\ntargets = ["cursor"]\n', "cursor.*allowed"),
        ("[apply]\ntargets = []\n", "at least one"),
        ('[apply]\nhomes = ".agents"\n', "unknown keys .'homes'."),
    ):
        (tmp_path / "sherpa.toml").write_text(bad, encoding="utf-8")
        with pytest.raises(ValueError, match=msg):
            load(tmp_path)


def test_resolve_layout_detects_asks_and_remembers(tmp_path: Path, monkeypatch):
    from sherpa.cli import _resolve_layout

    def layout(state=None, *, ask: bool, preview: bool = False):
        return _resolve_layout(tmp_path, state or State(), ask=ask, preview=preview)[:2]

    assert layout(ask=False) == (".agents", ("claude", "agents-md"))  # bare, no terminal
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    asked = []
    monkeypatch.setattr("builtins.input", lambda q: asked.append(q) or "")
    assert layout(ask=True)[0] == ".agents"  # bare: the user decides, Enter = default
    assert asked[-1].startswith("no harness directory yet — owner docs and skills under [1] .agents (default")
    monkeypatch.setattr("builtins.input", lambda q: asked.append(q) or "2")
    assert layout(ask=True)[0] == ".claude"
    (tmp_path / ".claude").mkdir()
    asked.clear()
    assert layout(ask=True) == (".claude", ("claude",)) and not asked  # one exists: no question
    (tmp_path / "AGENTS.md").write_text("# x\n", encoding="utf-8")
    assert layout(ask=False) == (".claude", ("claude", "agents-md"))
    (tmp_path / ".agents").mkdir()
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(ValueError, match="both .agents/ and .claude/ exist"):
        layout(ask=True)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    assert layout(ask=True)[0] == ".claude" and asked[-1].startswith("both .agents/ and .claude/ exist")
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert layout(ask=True)[0] == ".agents"
    # the state remembers, the config file wins
    assert layout(State(home=".claude", targets=("claude",)), ask=False) == (".claude", ("claude",))
    (tmp_path / "sherpa.toml").write_text('[apply]\nhome = ".agents"\ntargets = ["agents-md"]\n', encoding="utf-8")
    assert layout(State(home=".claude", targets=("claude",)), ask=False) == (".agents", ("agents-md",))


def test_resolve_layout_preview_assumes_agents_when_both_homes_exist(tmp_path: Path, monkeypatch):
    """ADR-0036: a preview never asks and never refuses — it assumes .agents and says so; a write still refuses."""
    from sherpa.cli import ASSUMED_HOME, _resolve_layout

    (tmp_path / ".claude").mkdir()
    (tmp_path / ".agents").mkdir()
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert _resolve_layout(tmp_path, State(), ask=False, preview=True) == (
        ".agents",
        ("claude", "agents-md"),
        [ASSUMED_HOME],
    )
    with pytest.raises(ValueError, match="both .agents/ and .claude/ exist"):
        _resolve_layout(tmp_path, State(), ask=False)  # --yes: a write never guesses
    # decided by the state, the checker copy or sherpa.toml: no assumption, no note
    assert _resolve_layout(tmp_path, State(home=".claude", targets=("claude",)), ask=False, preview=True) == (
        ".claude",
        ("claude",),
        [],
    )
    (tmp_path / ".claude" / "scripts").mkdir()
    (tmp_path / ".claude" / "scripts" / "sherpa-check.py").write_text("# copy\n", encoding="utf-8")
    assert _resolve_layout(tmp_path, State(), ask=False, preview=True) == (".claude", ("claude", "agents-md"), [])


def test_resolve_layout_refuses_a_repository_with_nested_repositories(tmp_path: Path):
    """ADR-0045: a directory anywhere in the tree with a .git inside — a harness clone under .claude/, a
    submodule, a vendored clone — means two repositories; sherpa works with one: the write refuses, a preview
    names them and goes on."""
    from sherpa import gitinfo
    from sherpa.cli import _resolve_layout

    layout = State(home=".agents", targets=("claude", "agents-md"))
    assert gitinfo.nested_repositories(tmp_path) == [] and _resolve_layout(tmp_path, layout, ask=False)[2] == []
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / ".git").mkdir()  # a clone
    line = (
        ".claude/ is a repository of its own (.claude/.git) — sherpa works with one repository: move the clone "
        "out of the tree, or run sherpa in that repository"
    )
    with pytest.raises(ValueError, match=re.escape(line)):
        _resolve_layout(tmp_path, layout, ask=False)
    assert _resolve_layout(tmp_path, layout, ask=False, preview=True) == (
        ".agents",
        ("claude", "agents-md"),
        [f"note: {line} — this preview goes on; `apply` and `adopt` refuse."],
    )
    # a worktree (.git is a file) deep in the tree, a submodule-like directory; node_modules is not walked
    (tmp_path / "src" / "vendor-lib").mkdir(parents=True)
    (tmp_path / "src" / "vendor-lib" / ".git").write_text("gitdir: ../../.git/modules/lib\n", encoding="utf-8")
    (tmp_path / "node_modules" / "pkg" / ".git").mkdir(parents=True)
    assert gitinfo.nested_repositories(tmp_path) == [".claude", "src/vendor-lib"]
    notes = _resolve_layout(tmp_path, layout, ask=False, preview=True)[2]
    assert notes[0].startswith("note: .claude/, src/vendor-lib/ are repositories of their own (.claude/.git)")
    for i in range(6):
        (tmp_path / "libs" / f"lib{i}" / ".git").mkdir(parents=True)
    notes = _resolve_layout(tmp_path, layout, ask=False, preview=True)[2]
    assert (
        ".claude/, libs/lib0/, libs/lib1/, libs/lib2/, libs/lib3/ and 3 more are repositories of their own" in notes[0]
    )


def test_cli_dry_run_assumes_a_home_and_the_write_refuses_without_a_terminal(active_repo: Path, capsys):
    from sherpa.cli import ASSUMED_HOME

    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    (active_repo / ".claude").mkdir()
    (active_repo / ".agents").mkdir()
    capsys.readouterr()
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("targets: claude, agents-md · home: .agents\n" + ASSUMED_HOME + "\n")
    assert ".agents/scripts/sherpa-check.py" in out and "to add" in out
    assert main(["adopt", str(active_repo), "--dry-run"]) == 0
    assert ASSUMED_HOME in capsys.readouterr().out
    assert main(["status", str(active_repo)]) == 0  # read-only: never refuses either — and says what it assumed (F56)
    assert "  " + ASSUMED_HOME in capsys.readouterr().out
    assert main(["status", str(active_repo), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["notes"][0] == ASSUMED_HOME.removeprefix("note: ")
    assert main(["apply", str(active_repo), "--yes"]) == 1
    assert 'Set [apply] home = ".agents" or ".claude" in sherpa.toml' in capsys.readouterr().err
    assert not (active_repo / ".agents" / "scripts").exists()


def test_cli_apply_and_adopt_refuse_a_nested_repository_and_the_previews_go_on(active_repo: Path, capsys):
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    (active_repo / ".claude").mkdir()
    (active_repo / ".claude" / ".git").mkdir()
    capsys.readouterr()
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "note: .claude/ is a repository of its own (.claude/.git) — sherpa works with one repository" in out
    assert "this preview goes on; `apply` and `adopt` refuse." in out and "to add" in out
    assert main(["apply", str(active_repo), "--yes"]) == 1
    err = capsys.readouterr().err
    assert err.startswith(
        "sherpa apply: .claude/ is a repository of its own (.claude/.git) — sherpa works with one repository"
    )
    assert not (active_repo / ".claude" / "hooks").exists()
    assert main(["adopt", str(active_repo), "--dry-run"]) == 0
    assert "note: .claude/ is a repository of its own" in capsys.readouterr().out
    assert main(["adopt", str(active_repo)]) == 1
    assert "sherpa adopt: .claude/ is a repository of its own" in capsys.readouterr().err
    assert main(["status", str(active_repo)]) == 0  # read-only: never refuses


def test_existing_nested_agents_md_gets_the_block_appended(active_repo: Path, capsys):
    nested = active_repo / "svc" / "pay" / "AGENTS.md"
    nested.write_text("# pay — team notes\n\nRun `make test` first.\n", encoding="utf-8")
    root = active_repo / "AGENTS.md"
    root.write_text("# shop\n\nHouse rules.\n", encoding="utf-8")
    applied(active_repo)
    out = capsys.readouterr().out
    assert "~ AGENTS.md" in out and "block harness appended" in out
    assert "~ svc/pay/AGENTS.md" in out and "block facts appended" in out
    text = nested.read_text(encoding="utf-8")
    assert text.startswith("# pay — team notes\n\nRun `make test` first.\n\n<!-- sherpa:begin facts -->")
    assert root.read_text(encoding="utf-8").startswith("# shop\n\nHouse rules.\n\n<!-- sherpa:begin harness -->")
    assert "targets: agents-md · home: .agents" in out and not (active_repo / "CLAUDE.md").exists()  # detected
    assert "note: no target with hooks" in out  # honest: no outcome labels without Claude Code
    assert main(["check", str(active_repo)]) == 0


def test_write_skips_a_file_that_changed_since_the_preview(tmp_path: Path):
    """Compare-and-swap (ADR-0030): the bytes were computed from the preview's read; a file that moved in
    between is never overwritten — managed, blocks and hooks alike — and its record stays as it was."""
    repo = tmp_path
    plan = build_plan(model([mod("a", "a", c90=1)]))
    doc = Target(".claude/docs/modules/a.md", MANAGED, None, "# a\n")
    root = Target("CLAUDE.md", BLOCKS, None, "", blocks={"facts": "one"}, append=True)
    (repo / "CLAUDE.md").write_text("# Theirs\n", encoding="utf-8")
    hooks = Target(
        ".claude/settings.json", JSON_HOOKS, None, "", hooks={"Stop": [{"hooks": [{"command": "x sherpa-outcome.py"}]}]}
    )
    r = write(plan_files([doc, root, hooks], repo, State()), repo, State(), plan)
    assert r.written == 3 and not r.rolled_back
    # second round: every file is planned as an update, then edited by somebody else before the write
    doc2 = Target(doc.path, MANAGED, None, "# a v2\n")
    root2 = Target(root.path, BLOCKS, None, "", blocks={"facts": "two"}, append=True)
    hooks2 = Target(
        hooks.path, JSON_HOOKS, None, "", hooks={"PreToolUse": [{"hooks": [{"command": "y sherpa-outcome.py"}]}]}
    )
    actions = plan_files([doc2, root2, hooks2], repo, r.state)
    assert [a.op for a in actions] == [UPDATED, UPDATED, UPDATED]
    (repo / doc.path).write_text("# a, mine now\n", encoding="utf-8")
    (repo / "CLAUDE.md").write_text(
        "Prose written while sherpa was waiting.\n" + (repo / "CLAUDE.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (repo / hooks.path).write_text('{"hooks": {}, "theirs": true}\n', encoding="utf-8")
    r2 = write(actions, repo, r.state, plan)
    assert r2.written == 0 and not r2.rolled_back
    assert [(a.op, a.detail) for a in r2.actions] == [(SKIPPED, apply.CHANGED_SINCE_PREVIEW)] * 3
    assert (repo / doc.path).read_text(encoding="utf-8") == "# a, mine now\n"
    assert (repo / "CLAUDE.md").read_text(encoding="utf-8").startswith("Prose written while sherpa was waiting.\n")
    assert "\none\n" in (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert (repo / hooks.path).read_text(encoding="utf-8") == '{"hooks": {}, "theirs": true}\n'
    assert r2.state.files == r.state.files  # records untouched: the next run plans against what is there now
    out = apply.render_result(r2)
    assert "  ! CLAUDE.md  changed since the preview (skipped)" in out and "0 files written" in out
    # the next preview sees the hand edits as such
    r3 = plan_files([doc2, root2, hooks2], repo, r2.state)
    assert r3[0].detail == "hand-edited (skipped)"


def test_write_skips_a_file_that_appeared_since_the_preview(tmp_path: Path):
    doc = Target(".claude/docs/modules/a.md", MANAGED, None, "# a\n")
    plan = build_plan(model([mod("a", "a", c90=1)]))
    actions = plan_files([doc], tmp_path, State())
    assert actions[0].op == NEW and actions[0].old is None
    (tmp_path / doc.path).parent.mkdir(parents=True)
    (tmp_path / doc.path).write_text("theirs\n", encoding="utf-8")
    r = write(actions, tmp_path, State(), plan)
    assert r.written == 0 and r.actions[0].op == SKIPPED and r.actions[0].detail == apply.CHANGED_SINCE_PREVIEW
    assert (tmp_path / doc.path).read_text(encoding="utf-8") == "theirs\n"
    assert doc.path not in r.state.files


def test_rollback_never_touches_a_file_skipped_since_the_preview(tmp_path: Path):
    """A rollback restores only what was written; the skipped file keeps the bytes somebody else put there."""
    repo = tmp_path
    plan = build_plan(model([mod("a", "a", c90=1)]))
    ok = Target(".claude/docs/modules/ok.md", MANAGED, None, "# ok\n")
    r = write(plan_files([ok], repo, State()), repo, State(), plan)
    ok2 = Target(ok.path, MANAGED, None, "# ok v2\n")
    bad = Target(".claude/docs/modules/bad.md", MANAGED, None, "<!-- sherpa:begin x -->\nnever closed\n")
    actions = plan_files([ok2, bad], repo, r.state)
    (repo / ok.path).write_text("# ok, mine\n", encoding="utf-8")
    r2 = write(actions, repo, r.state, plan)
    assert r2.rolled_back and r2.written == 0
    assert (repo / ok.path).read_text(encoding="utf-8") == "# ok, mine\n"
    assert not (repo / bad.path).exists()


def _symlink(link: Path, to: Path) -> None:
    try:
        link.symlink_to(to, target_is_directory=to.is_dir())
    except (OSError, NotImplementedError) as e:  # Windows without the privilege
        pytest.skip(f"symlinks not available here: {e}")


def test_plan_never_writes_through_a_symlink(tmp_path: Path):
    """ADR-0031: a symlink anywhere in the path — to a file outside the repo, to a sibling inside it, or a
    directory — is skipped in the preview; the bytes behind the link stay as they are."""
    repo = tmp_path / "repo"
    (repo / ".claude" / "docs").mkdir(parents=True)
    outside = tmp_path / "outside.md"
    outside.write_text("theirs, outside\n", encoding="utf-8")
    _symlink(repo / "AGENTS.md", outside)  # file link out of the repo
    (repo / "CLAUDE.md").write_text("# Theirs\n", encoding="utf-8")
    extern = tmp_path / "elsewhere"
    extern.mkdir()
    _symlink(repo / ".claude" / "docs" / "modules", extern)  # directory link out of the repo
    targets = [
        Target("AGENTS.md", BLOCKS, None, "", blocks={"harness": "x"}, append=True),
        Target("CLAUDE.md", BLOCKS, None, "", blocks={"harness": "x"}, append=True),
        Target(".claude/docs/modules/a.md", MANAGED, None, "# a\n"),
    ]
    actions = plan_files(targets, repo, State())
    assert [(a.op, a.detail) for a in actions[:1]] == [(SKIPPED, apply.THROUGH_SYMLINK)]
    assert actions[1].op == UPDATED  # the real file next to the link is fine
    assert (actions[2].op, actions[2].detail) == (SKIPPED, apply.THROUGH_SYMLINK)
    plan = build_plan(model([mod("a", "a", c90=1)]))
    r = write(actions, repo, State(), plan)
    assert r.written == 1 and outside.read_text(encoding="utf-8") == "theirs, outside\n" and not list(extern.iterdir())
    assert set(r.state.files) == {"CLAUDE.md"}
    out = render_actions(actions, plan)
    assert "! AGENTS.md" in out and "symlink in the path — never written through (skipped)" in out


def test_plan_never_writes_through_a_symlink_to_a_sibling(tmp_path: Path):
    """``AGENTS.md → CLAUDE.md`` is a common pattern: one file, one record — the link is skipped, the target managed."""
    (tmp_path / "CLAUDE.md").write_text("# Theirs\n", encoding="utf-8")
    _symlink(tmp_path / "AGENTS.md", tmp_path / "CLAUDE.md")
    targets = [
        Target("CLAUDE.md", BLOCKS, None, "", blocks={"harness": "x"}, append=True),
        Target("AGENTS.md", BLOCKS, None, "", blocks={"harness": "y"}, append=True),
    ]
    plan = build_plan(model([mod("a", "a", c90=1)]))
    r = write(plan_files(targets, tmp_path, State()), tmp_path, State(), plan)
    assert r.written == 1 and set(r.state.files) == {"CLAUDE.md"}
    text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert text.count("sherpa:begin") == 1 and "\nx\n" in text


def test_write_skips_a_path_that_became_a_symlink_since_the_preview(tmp_path: Path):
    doc = Target(".claude/docs/modules/a.md", MANAGED, None, "# a\n")
    plan = build_plan(model([mod("a", "a", c90=1)]))
    actions = plan_files([doc], tmp_path, State())
    assert actions[0].op == NEW
    outside = tmp_path / "outside.md"
    outside.write_text("theirs\n", encoding="utf-8")
    (tmp_path / doc.path).parent.mkdir(parents=True)
    _symlink(tmp_path / doc.path, outside)
    r = write(actions, tmp_path, State(), plan)
    assert r.written == 0 and r.actions[0].detail == apply.CHANGED_SINCE_PREVIEW
    assert outside.read_text(encoding="utf-8") == "theirs\n" and not r.state.files


def test_write_rolls_back_when_a_write_fails_half_way(tmp_path: Path, monkeypatch):
    """ADR-0032: an OSError on the second file removes the first again; the state stays as it was."""
    repo = tmp_path
    plan = build_plan(model([mod("a", "a", c90=1)]))
    one = Target(".claude/docs/modules/one.md", MANAGED, None, "# one\n")
    two = Target(".claude/docs/modules/two.md", MANAGED, None, "# two\n")
    r = write(plan_files([two], repo, State()), repo, State(), plan)
    before = (repo / ".sherpa/state.json").read_bytes()
    real = apply.atomic.write_text

    def failing(path: Path, text: str) -> None:
        if path.name == "two.md":
            raise OSError(28, "No space left on device")
        real(path, text)

    monkeypatch.setattr(apply.atomic, "write_text", failing)
    two2 = Target(two.path, MANAGED, None, "# two v2\n")
    r2 = write(plan_files([one, two2], repo, r.state), repo, r.state, plan)
    assert r2.rolled_back and r2.written == 0 and r2.left == []
    assert r2.error == ".claude/docs/modules/two.md: [Errno 28] No space left on device"
    assert not (repo / one.path).exists()  # the new file is gone again
    assert (repo / two.path).read_text(encoding="utf-8") == "# two\n"  # the old one untouched
    assert (repo / ".sherpa/state.json").read_bytes() == before
    out = apply.render_result(r2)
    assert (
        out
        == "write failed: .claude/docs/modules/two.md: [Errno 28] No space left on device — rolled back, nothing written\n"
    )


def test_write_names_what_a_failed_rollback_left_behind(tmp_path: Path, monkeypatch):
    repo = tmp_path
    plan = build_plan(model([mod("a", "a", c90=1)]))
    one = Target(".claude/docs/modules/one.md", MANAGED, None, "# one\n")
    two = Target(".claude/docs/modules/two.md", MANAGED, None, "# two\n")
    r = write(plan_files([one], repo, State()), repo, State(), plan)
    calls = {"n": 0}
    real = apply.atomic.write_text

    def failing(path: Path, text: str) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            real(path, text)  # one.md v2 lands
        else:
            raise OSError(30, "Read-only file system")  # two.md fails, and so does restoring one.md

    monkeypatch.setattr(apply.atomic, "write_text", failing)
    one2 = Target(one.path, MANAGED, None, "# one v2\n")
    r2 = write(plan_files([one2, two], repo, r.state), repo, r.state, plan)
    assert r2.rolled_back and r2.left == [".claude/docs/modules/one.md"]
    assert (repo / one.path).read_text(encoding="utf-8") == "# one v2\n"
    out = apply.render_result(r2)
    assert "rollback failed for: .claude/docs/modules/one.md — restore with `git checkout -- <path>`" in out
    assert "`sherpa adopt` rebuilds the state" in out


def test_write_is_atomic_per_file(tmp_path: Path, monkeypatch):
    """The target is never observed truncated: the bytes go to a sibling temp file, then ``os.replace``."""
    repo = tmp_path
    doc = repo / ".claude/docs/modules/a.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("# old\n", encoding="utf-8")
    seen = []
    real_replace = os.replace

    def spying_replace(src, dst):
        seen.append((Path(src).name, Path(dst).read_text(encoding="utf-8")))
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", spying_replace)
    apply.atomic.write_text(doc, "# new\n")
    assert seen == [(f".a.md.{os.getpid()}.tmp", "# old\n")]  # the old file was intact right before the swap
    assert doc.read_text(encoding="utf-8") == "# new\n" and sorted(p.name for p in doc.parent.iterdir()) == ["a.md"]


@pytest.mark.parametrize(
    "command,expected",
    [
        # runs
        ("pytest -q tests", True),
        (".venv/bin/pytest -q", True),
        ("python -m pytest -x", True),
        ("cd svc && FOO=1 python3 -m pytest", True),
        ("uv run pytest", True),
        ("poetry run pytest tests/", True),
        ("npx jest --ci", True),
        ("npm test", True),
        ("npm run test:unit", True),
        ("pnpm run test", True),
        ("dotnet test Shop.sln", True),
        ("sudo dotnet test", True),
        ("go test ./...", True),
        ("cargo test --workspace", True),
        ("make test", True),
        ("git pull && pytest", True),
        ("ls | pytest", True),
        ("C:\\venv\\Scripts\\pytest.exe -q", True),
        # not runs — the finding: the word somewhere in the line
        ("cat pytest.ini", False),
        ("pip install pytest", False),
        ("uv add --dev pytest", False),
        ("grep -rn pytest README.md", False),
        ("echo jest", False),
        ("git commit -m 'add pytest config'", False),
        ("python pytest.py", False),
        ("pytest_helper.py", False),
        ("cat docs/go test.md", False),
        ("npm run build", False),
        ("git push && gh pr create", False),
    ],
)
def test_outcome_hook_recognises_a_test_run_only_as_the_command_word(command, expected):
    """ADR-0040: the fixed input matrix for the classifier — a test run is a runner as the command word of a
    shell segment, never the word somewhere in the line. Both sides of the matrix grow with every new runner."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("sherpa_outcome", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.is_test_run(command) is expected


def test_outcome_hook_stamps_the_revision_the_execution_started_with(tmp_path: Path):
    """ADR-0040: `sherpa apply` inside an execution changes the state; the label belongs to the harness the agent
    worked with, and the end revision is kept next to it so the evaluation can leave such runs out."""
    state = tmp_path / ".sherpa" / "state.json"
    state.parent.mkdir()
    state.write_text(json.dumps({"harness_rev": "aaaaaaaaaaaa"}), encoding="utf-8")
    s = "s2"
    fire(tmp_path, {"hook_event_name": "UserPromptSubmit", "session_id": s, "prompt": "apply the harness"})
    fire(
        tmp_path,
        {
            "hook_event_name": "PostToolUse",
            "session_id": s,
            "tool_name": "Bash",
            "tool_input": {"command": "cat pytest.ini"},
        },
    )
    state.write_text(json.dumps({"harness_rev": "bbbbbbbbbbbb"}), encoding="utf-8")  # sherpa apply ran
    fire(tmp_path, {"hook_event_name": "Stop", "session_id": s})
    rec = labels(tmp_path)[0]
    assert rec["harness_rev"] == "aaaaaaaaaaaa" and rec["harness_rev_at_stop"] == "bbbbbbbbbbbb"
    assert rec["label"] == "unknown" and rec["signals"]["tests_run"] == 0, "`cat pytest.ini` is not a green test"
    fire(tmp_path, {"hook_event_name": "UserPromptSubmit", "session_id": s, "prompt": "next"})
    fire(tmp_path, {"hook_event_name": "Stop", "session_id": s})
    rec = labels(tmp_path)[1]
    assert rec["harness_rev"] == "bbbbbbbbbbbb" and "harness_rev_at_stop" not in rec


def test_status_names_plan_for_a_model_from_another_schema(active_repo: Path, capsys):
    """After an upgrade that bumps the model schema, every reader says what rebuilds it — `plan` rescans."""
    applied(active_repo)
    mp = active_repo / ".sherpa" / "codebase-model.json"
    d = json.loads(mp.read_text(encoding="utf-8"))
    d["schema_version"] = 4
    mp.write_text(json.dumps(d), encoding="utf-8")
    assert main(["status", str(active_repo)]) == 1
    assert "model has schema_version 4, expected 5 — run `sherpa plan` (it rescans)" in capsys.readouterr().err
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0 and main(["status", str(active_repo)]) == 0


def test_cli_rollback_names_itself_on_stderr_too(active_repo: Path, monkeypatch, capsys):
    """files-and-exit-codes.md: errors reach stderr as `sherpa <command>: …` — a rollback included, so a CI job that
    watches stderr sees it; the details stay on stdout (e2e 0.8.1, open item 1)."""
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    real = apply.atomic.write_text

    def failing(path: Path, text: str) -> None:
        if path.name == "pay.md":
            raise OSError(28, "No space left on device")
        real(path, text)

    monkeypatch.setattr(apply.atomic, "write_text", failing)
    capsys.readouterr()
    assert main(["apply", str(active_repo), "--yes"]) == 1
    out, err = capsys.readouterr()
    assert out.rstrip().endswith("[Errno 28] No space left on device — rolled back, nothing written")
    assert (
        err
        == "sherpa apply: write failed: .agents/docs/modules/pay.md: [Errno 28] No space left on device — rolled back, nothing written\n"
    )
    assert not (active_repo / ".agents").exists() and not (active_repo / ".claude").exists()


def test_apply_header_counts_the_selected_entries(active_repo: Path, capsys):
    """`N selected` is the number of entries apply renders for, the outcome entry included although its files
    (hook, settings) carry no entry tag — the plan's rejects come off the count (e2e 0.8.1, open item 5)."""
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    capsys.readouterr()
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    head = capsys.readouterr().out.splitlines()[1]
    assert re.search(r": 10 entries, 6 selected → \d+ files$", head), head  # 6 proposals, none rejected
    assert main(["plan", str(active_repo), "--no-fetch", "--reject", "agent:pay"]) == 0
    capsys.readouterr()
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    assert ": 10 entries, 5 selected → " in capsys.readouterr().out.splitlines()[1]


def test_apply_warn_count_equals_check_right_after(active_repo: Path, capsys):
    """§13 F52: the post-write check runs against the state this run wrote, so the WARN count `apply` prints
    (C8 drift included) is the one `sherpa check` prints right after — not one measured against the old state."""
    applied(active_repo)
    assert main(["plan", str(active_repo), "--no-fetch", "--reject", "owner-doc:core"]) == 0
    capsys.readouterr()
    assert main(["apply", str(active_repo), "--yes"]) == 0
    out = capsys.readouterr().out
    m = re.search(r"^check: (\d+) FAIL, (\d+) WARN$", out, re.M)
    assert m and "removed · harness_rev" in out, out
    from sherpa.check import FAIL, check

    after = check(active_repo)
    assert (int(m.group(1)), int(m.group(2))) == (
        sum(f.level == FAIL for f in after),
        sum(f.level != FAIL for f in after),
    ), (out, after)
    assert int(m.group(2)) == 0, "a removal that the state records is no drift"
