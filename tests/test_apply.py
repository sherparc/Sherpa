"""``sherpa apply`` and ``status``: rendering, ownership modes, write/state/rollback, idempotency, CLI, goldens."""

from __future__ import annotations

import hashlib
import json
import os
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
from tests.conftest import commit
from tests.test_plan import active_repo, check_golden, mod, model  # noqa: F401 — fixture and builders


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
    m = model([mod("app", "", c90=30, c30=30, authors=2, files=40)])
    by_path = {t.path: t for t in targets_for(build_plan(m), m, targets=("agents-md",))}
    assert "## app (managed by sherpa" in by_path["AGENTS.md"].blocks["harness"]
    assert not any(p.endswith("/AGENTS.md") for p in by_path) and "CLAUDE.md" not in by_path


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


def test_apply_is_idempotent_and_deterministic(active_repo: Path, capsys):  # noqa: F811
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


def test_harness_rev_changes_only_with_managed_content():
    files = {"a": FileRecord(MANAGED, hash="a" * 16), "b": FileRecord(BLOCKS, blocks={"x": "b" * 16})}
    rev = state_mod.harness_rev(files)
    assert rev == state_mod.harness_rev(dict(reversed(list(files.items()))))
    assert rev != state_mod.harness_rev({**files, "b": FileRecord(BLOCKS, blocks={"x": "c" * 16})})
    assert rev != state_mod.harness_rev(files, version="9.9.9")


def test_rescan_updates_the_facts_block_and_keeps_human_text(active_repo: Path, capsys):  # noqa: F811
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


def test_status_reports_drift_orphans_outcomes_and_version(active_repo: Path, capsys):  # noqa: F811
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
                json.dumps({"kind": "outcome", "harness_rev": "000000000000", "label": "failed"}),
                json.dumps({"kind": "correction", "harness_rev": st.harness_rev}),
                "not json",
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
    assert "  ? .claude/agents/old.md            in the state, no longer in the plan" in out
    assert "  - .agents/docs/modules/core.md     in the state, not on disk — apply recreates it" in out
    assert "  ! .claude/hooks/sherpa-outcome.py  hand-edited (skipped)" in out
    assert "  ! .agents/scripts/sherpa-check.py  hand-edited (skipped)" in out
    assert "outcomes: 3 executions labelled, 1 corrections\n" in out
    assert (
        f"  {st.harness_rev} (current): 1 success, 0 failed, 1 unknown\n  000000000000: 0 success, 1 failed, 0 unknown\n"
        in out
    )
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


def test_cli_apply_dry_run_asks_and_aborts(active_repo: Path, capsys, monkeypatch):  # noqa: F811
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


def test_cli_check_and_adopt(active_repo: Path, capsys):  # noqa: F811
    applied(active_repo)
    capsys.readouterr()
    assert main(["check", str(active_repo)]) == 0
    assert capsys.readouterr().out.startswith(f"sherpa check {active_repo.resolve()}: 0 FAIL, 0 WARN\n")
    assert main(["check", str(active_repo), "--json"]) == 0 and capsys.readouterr().out == "[]\n"
    assert main(["adopt", str(active_repo)]) == 2


# ---------------------------------------------------------------- goldens (the README shows these)


def test_active_fixture_goldens(active_repo: Path, capsys):  # noqa: F811
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

    assert _resolve_layout(tmp_path, State(), ask=False) == (".agents", ("claude", "agents-md"))  # bare, no terminal
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    asked = []
    monkeypatch.setattr("builtins.input", lambda q: asked.append(q) or "")
    assert _resolve_layout(tmp_path, State(), ask=True)[0] == ".agents"  # bare: the user decides, Enter = default
    assert asked[-1].startswith("no harness directory yet — owner docs and skills under [1] .agents (default")
    monkeypatch.setattr("builtins.input", lambda q: asked.append(q) or "2")
    assert _resolve_layout(tmp_path, State(), ask=True)[0] == ".claude"
    (tmp_path / ".claude").mkdir()
    asked.clear()
    assert (
        _resolve_layout(tmp_path, State(), ask=True) == (".claude", ("claude",)) and not asked
    )  # one exists: no question
    (tmp_path / "AGENTS.md").write_text("# x\n", encoding="utf-8")
    assert _resolve_layout(tmp_path, State(), ask=False) == (".claude", ("claude", "agents-md"))
    (tmp_path / ".agents").mkdir()
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(ValueError, match="both .agents/ and .claude/ exist"):
        _resolve_layout(tmp_path, State(), ask=True)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    assert _resolve_layout(tmp_path, State(), ask=True)[0] == ".claude" and asked[-1].startswith(
        "both .agents/ and .claude/ exist"
    )
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert _resolve_layout(tmp_path, State(), ask=True)[0] == ".agents"
    # the state remembers, the config file wins
    assert _resolve_layout(tmp_path, State(home=".claude", targets=("claude",)), ask=False) == (".claude", ("claude",))
    (tmp_path / "sherpa.toml").write_text('[apply]\nhome = ".agents"\ntargets = ["agents-md"]\n', encoding="utf-8")
    assert _resolve_layout(tmp_path, State(home=".claude", targets=("claude",)), ask=False) == (
        ".agents",
        ("agents-md",),
    )


def test_cli_apply_refuses_ambiguous_home_without_terminal(active_repo: Path, capsys):  # noqa: F811
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    (active_repo / ".claude").mkdir()
    (active_repo / ".agents").mkdir()
    capsys.readouterr()
    assert main(["apply", str(active_repo), "--dry-run"]) == 1
    assert 'Set [apply] home = ".agents" or ".claude" in sherpa.toml' in capsys.readouterr().err


def test_existing_nested_agents_md_gets_the_block_appended(active_repo: Path, capsys):  # noqa: F811
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
