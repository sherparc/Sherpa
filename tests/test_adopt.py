"""``sherpa adopt``: classification, linking, covering plan entries, never touching a byte, rebuilding a lost state."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from sherpa import __version__, atomic
from sherpa.apply import state as state_mod
from sherpa.apply.adopt import Found, covers_by_path, kind_of, link, own_prose
from sherpa.apply.render import selected
from sherpa.apply.state import ADOPTED, GENERATED
from sherpa.cli import main
from sherpa.plan import PROPOSE, Entry, Plan, yamlio
from tests.conftest import commit, git
from tests.test_apply import applied
from tests.test_apply import tree_hash as _tree_hash
from tests.test_plan import check_golden


def tree_hash(repo: Path) -> str:
    """The repository without ``.sherpa/`` — adopt writes the state and the plan marks, nothing else."""
    return _tree_hash(repo) if not (repo / ".sherpa").exists() else _tree_hash_without_sherpa(repo)


def _tree_hash_without_sherpa(repo: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    for p in sorted(x for x in repo.rglob("*") if x.is_file() and not {".git", ".sherpa"} & set(x.parts)):
        h.update(p.relative_to(repo).as_posix().encode())
        h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def test_kind_of_classifies_by_path_only():
    cases = {
        "CLAUDE.md": "root",
        "AGENTS.md": "root",
        "svc/pay/AGENTS.md": "nested",
        ".claude/agents/pay.md": "agent",
        ".claude/skills/deploy/SKILL.md": "skill",
        ".agents/skills/deploy/SKILL.md": "skill",
        ".claude/commands/sync.md": "command",
        ".claude/docs/modules/pay.md": "doc",
        ".agents/docs/modules/pay.md": "doc",
        ".claude/hooks/sherpa-outcome.py": "hook",
        ".claude/settings.json": "settings",
        ".agents/scripts/sherpa-check.py": "script",
        ".claude/evals/golden.md": "eval",
        ".claude/notes.txt": "unknown",
        ".agents/agents/x.md": "unknown",  # agents live under .claude only
        "docs/x.md": "unknown",
    }
    assert {p: kind_of(p) for p in cases} == cases


def found(path: str, text: str, name: str | None = None) -> Found:
    return Found(path, kind_of(path), text.count("\n") + 1, text, name)


def test_link_by_name_then_by_mentions_then_nothing():
    units = {"Shop.Pay": "svc/pay", "Shop.Core": "svc/core", "suite": "tests/suite"}
    assert link(found(".claude/agents/shop-pay.md", "x"), units) == ("Shop.Pay", "name matches")
    assert link(found(".claude/skills/shop-core/SKILL.md", "x"), units) == ("Shop.Core", "name matches")
    assert link(found(".claude/agents/a.md", "x", name="Shop Pay"), units) == ("Shop.Pay", "front matter name matches")
    text = "Owns svc/pay/models.py and svc/pay/views.py; imports svc/core once.\n"
    assert link(found(".claude/agents/a.md", text), units) == ("Shop.Pay", "mentions svc/pay 2×")
    assert link(found(".claude/agents/a.md", "svc/pay once\n"), units) == (None, "no unit matches")
    tie = "svc/pay svc/pay svc/core svc/core\n"
    assert link(found(".claude/agents/a.md", tie), units) == (
        None,
        "ambiguous: Shop.Core and Shop.Pay mentioned 2× each",
    )
    # a nested unit path is a mention of the parent too, but the deeper unit wins the tie
    nested = {"Shop": "svc", "Shop.Pay": "svc/pay"}
    assert link(found(".claude/agents/a.md", "svc/pay/x svc/pay/y\n"), nested) == ("Shop.Pay", "mentions svc/pay 2×")


def existing_harness(repo: Path) -> None:
    fat = "---\nname: pay-expert\ndescription: pay\n---\n" + "\n".join(
        f"Line {i} about svc/pay code." for i in range(170)
    )
    files = {
        ".claude/agents/pay-expert.md": fat + "\n",
        ".claude/agents/ops.md": "---\nname: ops\ndescription: ops\n---\nDeploys the thing.\n",
        ".claude/docs/modules/pay.md": "# pay\n\nHand-written owner doc.\n",
        ".claude/docs/modules/legacy.md": "# legacy\n\nNothing in the repo matches.\n",
        ".claude/commands/deploy.md": "Run the deploy.\n",
        ".claude/notes.txt": "misc\n",
        ".claude/settings.local.json": "{}\n",
        ".claude/memory/private.md": "not the harness\n",
        ".gitignore": ".claude/memory/\n",
        "CLAUDE.md": "# Shop\n\nHand-written.\n",
    }
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def test_adopt_takes_over_without_touching_a_byte_and_covers_entries(active_repo: Path, capsys):
    existing_harness(active_repo)
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    before = tree_hash(active_repo)
    assert main(["adopt", str(active_repo)]) == 0
    out = capsys.readouterr().out
    assert tree_hash(active_repo) == before, "adopt changed a harness file"
    assert "home .claude · targets claude" in out
    assert "a .claude/agents/pay-expert.md" in out and "→ agent pay (mentions svc/pay 170×)" in out
    assert "a .claude/agents/ops.md" in out and "no unit matches" in out
    assert "a .claude/docs/modules/pay.md" in out and "at sherpa's path, yours — covers the entry" in out
    assert "? .claude/notes.txt" in out and "settings.local.json" not in out and "memory" not in out
    assert "· CLAUDE.md" in out and "`apply` appends its block" in out
    assert ".claude/agents/pay-expert.md: 175 lines, no knowledge manifest — rotation candidate" in out
    assert ".claude/docs/modules/legacy.md: no unit matches" in out
    assert "2 proposed owner docs without an existing doc" in out
    assert "1 file of unknown kind" in out
    assert "2 plan entries covered" in out

    state = state_mod.load(active_repo / state_mod.STATE_PATH)
    assert state.home == ".claude" and state.targets == ("claude",)
    recs = {p: r for p, r in state.files.items() if r.origin == ADOPTED}
    assert recs[".claude/agents/pay-expert.md"].entry == "agent:pay:svc/pay"
    assert recs[".claude/docs/modules/pay.md"].entry == "owner-doc:pay:svc/pay"
    assert recs[".claude/agents/ops.md"].entry is None and recs[".claude/notes.txt"].entry is None
    assert "CLAUDE.md" not in state.files  # apply may still append its block (ADR-0016)

    plan = yamlio.plan_from_dict(yamlio.load(active_repo / ".sherpa" / "harness-plan.yaml"))
    covered = {(e.kind, e.target): e.covered for e in plan.entries if e.covered}
    assert covered == {
        ("agent", "pay"): ".claude/agents/pay-expert.md",
        ("owner-doc", "pay"): ".claude/docs/modules/pay.md",
    }
    assert {(e.kind, e.target) for e in selected(plan)}.isdisjoint(covered)
    accepted = replace(plan, entries=[replace(e, decision="accept") if e.covered else e for e in plan.entries])
    assert {(e.kind, e.target) for e in selected(accepted)} >= set(covered)  # explicit accept overrides

    # apply renders nothing for covered entries, points the proximity file at the adopted doc, never touches
    # adopted files — and a re-plan keeps the marks
    assert main(["apply", str(active_repo), "--yes"]) == 0
    out = capsys.readouterr().out
    assert ".claude/agents/pay.md" not in out and "! .claude/docs/modules/pay.md" not in out
    assert "+ CLAUDE.md" not in out and "~ CLAUDE.md" in out and "block harness appended" in out
    nested = (active_repo / "svc/pay/CLAUDE.md").read_text(encoding="utf-8")
    assert "../../.claude/docs/modules/pay.md" in nested
    assert (active_repo / ".claude/docs/modules/pay.md").read_text(
        encoding="utf-8"
    ) == "# pay\n\nHand-written owner doc.\n"
    assert (active_repo / "CLAUDE.md").read_text(encoding="utf-8").startswith("# Shop\n\nHand-written.\n")
    assert tree_hash(active_repo) != before  # apply did add sherpa's own files
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    assert "2 covered by existing files" in capsys.readouterr().out
    assert main(["status", str(active_repo)]) == 0
    out = capsys.readouterr().out
    assert "note: 6 adopted files are yours and never touched" in out and "drift: none" in out

    # a hand edit to an adopted file is not drift, not C8, and apply still leaves it alone
    (active_repo / ".claude/agents/ops.md").write_text("---\nname: ops\ndescription: ops\n---\nChanged.\n", "utf-8")
    assert main(["status", str(active_repo)]) == 0
    out = capsys.readouterr().out
    assert "ops.md" not in out and "C8" not in out
    # gone: reported once, dropped by the next adopt
    (active_repo / ".claude/agents/ops.md").unlink()
    assert main(["status", str(active_repo)]) == 0
    assert "- .claude/agents/ops.md" in capsys.readouterr().out
    assert main(["adopt", str(active_repo)]) == 0
    assert "dropped from the state (file gone): .claude/agents/ops.md" in capsys.readouterr().out


def test_adopt_refuses_a_home_that_is_a_repository_of_its_own(active_repo: Path, capsys):
    """ADR-0045: a `.claude/` that is a clone of its own is not this repository's harness — adopt refuses instead
    of reading it through the outer repository's ignore rules, which usually exclude the clone whole."""
    existing_harness(active_repo)
    git(active_repo / ".claude", "init", "-q")
    (active_repo / ".git" / "info" / "exclude").write_text(".claude/*\n", encoding="utf-8")
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    assert main(["adopt", str(active_repo)]) == 1
    err = capsys.readouterr().err
    assert "sherpa adopt: .claude/ is a repository of its own (.claude/.git) — sherpa works with one repository" in err
    assert not (active_repo / ".sherpa" / "state.json").exists()


def test_a_hand_set_cover_survives_the_replan_and_reaches_the_state(active_repo: Path, capsys):
    """ADR-0046: `covered:` written by a human — for a doc whose name matches no unit — is kept like a decision,
    honoured by adopt over its own linking and by apply, and dropped with a note when the file is gone."""
    existing_harness(active_repo)
    (active_repo / ".claude/docs/modules/legacy.md").write_text("# legacy\n\nThe owner doc of svc/web.\n", "utf-8")
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    plan_path = active_repo / ".sherpa" / "harness-plan.yaml"
    text = plan_path.read_text(encoding="utf-8")
    assert "covered:" not in text and "  target: web\n  scope: svc/web\n" in text
    plan_path.write_text(
        text.replace(
            "  target: web\n  scope: svc/web\n",
            "  target: web\n  scope: svc/web\n  covered: .claude/docs/modules/legacy.md\n",
            1,
        ),
        encoding="utf-8",
    )
    capsys.readouterr()
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    out = capsys.readouterr().out
    assert "owner-doc   web" in out and "[covered by .claude/docs/modules/legacy.md]" in out
    assert "1 covered by existing files" in out
    assert main(["adopt", str(active_repo)]) == 0
    out = capsys.readouterr().out
    assert "a .claude/docs/modules/legacy.md" in out and "→ owner-doc web (covered: set in the plan)" in out
    assert "legacy.md: no unit matches" not in out
    state = state_mod.load(active_repo / state_mod.STATE_PATH)
    assert state.files[".claude/docs/modules/legacy.md"].entry == "owner-doc:web:svc/web"
    assert main(["apply", str(active_repo), "--yes"]) == 0
    assert "docs/modules/web.md" not in capsys.readouterr().out
    assert "../../.claude/docs/modules/legacy.md" in (active_repo / "svc/web/CLAUDE.md").read_text(encoding="utf-8")
    # the file goes: the next plan says so and renders the doc again
    (active_repo / ".claude/docs/modules/legacy.md").unlink()
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    out = capsys.readouterr().out
    assert (
        "owner-doc:web:svc/web was covered by .claude/docs/modules/legacy.md, which no longer exists — dropped" in out
    )
    assert "[covered by .claude/docs/modules/legacy.md]" not in out


def test_adopt_rebuilds_a_lost_or_torn_state(active_repo: Path, capsys):
    applied(active_repo)
    state_path = active_repo / state_mod.STATE_PATH
    rev = state_mod.load(state_path).harness_rev
    before = tree_hash(active_repo)
    state_path.write_text('{"schema_version": 1, "files": {', encoding="utf-8")  # torn write
    assert main(["status", str(active_repo)]) == 0, "a torn index never blocks the diagnostic command (ADR-0034)"
    assert "`sherpa adopt` rebuilds it from the harness files" in capsys.readouterr().err
    assert main(["adopt", str(active_repo)]) == 0
    out, err = capsys.readouterr()
    assert "`sherpa adopt` rebuilds it" in err and "0 adopted" in out and " kept" in out
    state = state_mod.load(state_path)
    assert all(r.origin == GENERATED for r in state.files.values())
    assert state.harness_rev == rev, "the rebuilt state is the one apply wrote"
    assert tree_hash(active_repo) == before
    assert main(["apply", str(active_repo), "--yes"]) == 0
    assert "nothing to do." in capsys.readouterr().out
    # second adopt keeps every record (hashes match) and writes the same state again
    assert main(["adopt", str(active_repo)]) == 0
    assert f"0 adopted, 0 rebuilt, {len(state.files)} kept, 0 dropped" in capsys.readouterr().out


def test_adopt_keeps_hand_edits_in_blocks_and_in_base_files(active_repo: Path, capsys):
    """ADR-0033: a differing base file is yours after adopt — the next apply keeps it and says so; the gap
    line names the way to a fresh copy."""
    applied(active_repo)
    nested = active_repo / "svc/pay/AGENTS.md"
    text = nested.read_text(encoding="utf-8")
    nested.write_text(text.replace("| unit |", "| UNIT |"), encoding="utf-8")  # hand edit inside the block
    script = active_repo / ".agents/scripts/sherpa-check.py"
    script.write_text(
        script.read_text(encoding="utf-8").replace('SHERPA_VERSION = "', 'SHERPA_VERSION = "0.0.'), "utf-8"
    )
    (active_repo / state_mod.STATE_PATH).unlink()
    assert main(["adopt", str(active_repo)]) == 0
    out = capsys.readouterr().out
    assert "0 of 1 blocks match the plan; block facts differs (hand edit) — stays" in out
    assert "a .agents/scripts/sherpa-check.py" in out and "differs from sherpa's copy — yours" in out
    assert (
        f"  - .agents/scripts/sherpa-check.py: differs from sherpa {__version__}'s copy — yours; delete it and run "
        "`apply` for the current one" in out
    )
    state = state_mod.load(active_repo / state_mod.STATE_PATH)
    assert state.files["svc/pay/AGENTS.md"].blocks == {}
    assert state.files[".agents/scripts/sherpa-check.py"].origin == ADOPTED
    edited = script.read_text(encoding="utf-8")
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "! svc/pay/AGENTS.md" in out and "block facts not written by sherpa" in out
    assert "! .agents/scripts/sherpa-check.py" in out and "adopted — yours, never touched (skipped)" in out
    assert main(["apply", str(active_repo), "--yes"]) == 0
    assert script.read_text(encoding="utf-8") == edited  # the hand edit survives the write
    script.unlink()  # the documented way to a fresh copy
    assert main(["adopt", str(active_repo)]) == 0 and main(["apply", str(active_repo), "--yes"]) == 0
    assert f'SHERPA_VERSION = "{__version__}"' in script.read_text(encoding="utf-8")


def test_adopt_recognises_an_older_stamp_and_apply_refreshes_it(active_repo: Path, capsys):
    """A harness written by sherpa ≤ 0.5.0 carries ``origin/main@<rev>, as of <date>`` in every block. A rebuild
    after the upgrade must still call those blocks sherpa's (ADR-0022) — otherwise a lost state would freeze the
    whole harness as "hand-edited"."""
    applied(active_repo)
    state = state_mod.load(active_repo / state_mod.STATE_PATH)
    rev = state.plan["rev"][:10]
    touched = 0
    for rel in ("svc/pay/AGENTS.md", ".agents/docs/modules/pay.md", ".claude/agents/pay.md"):
        f = active_repo / rel
        old = f.read_text(encoding="utf-8")
        new = old.replace("as of 2026-03-01", f"origin/main@{rev}, as of 2026-03-01")
        assert new != old, rel
        f.write_text(new, encoding="utf-8")
        touched += 1
    assert touched == 3
    (active_repo / state_mod.STATE_PATH).unlink()
    assert main(["adopt", str(active_repo)]) == 0
    out = capsys.readouterr().out
    assert "carries an older stamp — `apply` refreshes it" in out and "(hand edit)" not in out
    rebuilt = state_mod.load(active_repo / state_mod.STATE_PATH)
    assert set(rebuilt.files["svc/pay/AGENTS.md"].blocks) == {"facts"}
    assert main(["apply", str(active_repo), "--yes"]) == 0
    out = capsys.readouterr().out
    assert "~ svc/pay/AGENTS.md" in out and "3 files written" in out
    assert f"origin/main@{rev}" not in (active_repo / "svc/pay/AGENTS.md").read_text(encoding="utf-8")
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    assert "nothing to do." in capsys.readouterr().out


def test_adopt_dry_run_and_settings_without_hook(active_repo: Path, capsys):
    (active_repo / ".claude").mkdir()
    (active_repo / ".claude/settings.json").write_text('{"permissions": {}}\n', encoding="utf-8")
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    assert main(["adopt", str(active_repo), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "· .claude/settings.json" in out and "no sherpa hook — `apply` merges it in" in out
    assert "state not written" in out and not (active_repo / state_mod.STATE_PATH).exists()
    assert main(["adopt", str(active_repo)]) == 0
    assert "nothing to adopt" in capsys.readouterr().out and not (active_repo / state_mod.STATE_PATH).exists()


def test_atomic_write_leaves_no_temp_file(tmp_path: Path):
    p = tmp_path / "x" / "state.json"
    atomic.write_text(p, "1\n")
    atomic.write_text(p, "2\n")
    assert p.read_text() == "2\n" and sorted(q.name for q in p.parent.iterdir()) == ["state.json"]
    with pytest.raises(TypeError):
        atomic.write_text(p, None)  # type: ignore[arg-type]
    assert p.read_text() == "2\n" and sorted(q.name for q in p.parent.iterdir()) == ["state.json"]


def test_state_load_names_the_way_out(tmp_path: Path):
    p = tmp_path / "state.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="sherpa adopt"):
        state_mod.load(p)
    p.write_text(json.dumps({"schema_version": 1, "sherpa": "x", "files": {"a": {"mode": "managed"}}}), "utf-8")
    assert state_mod.load(p).files["a"].origin == GENERATED


def test_existing_harness_goldens(active_repo: Path, capsys):
    """The README shows these: adopt on a hand-written harness, then the plan with covered entries."""
    existing_harness(active_repo)
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    capsys.readouterr()
    assert main(["adopt", str(active_repo)]) == 0
    check_golden("active-adopt-console.txt", capsys.readouterr().out)
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    out = capsys.readouterr().out
    assert out.endswith("harness-plan.yaml (2 covered by existing files)\n")
    check_golden("active-plan-covered-console.txt", out[: out.rindex("→ ")])


def test_adopt_and_plan_run_on_a_torn_state_after_the_trunk_moved(active_repo: Path, capsys):
    """ADR-0034: the recovery dead end — a torn state and a moved trunk. ``plan`` must not fail on the index it
    does not own, and ``adopt`` must not refuse a stale plan: it imports what is there, like ``terraform import``.
    Before, ``plan`` said "run adopt" and ``adopt`` said "run plan", both exit 1."""
    applied(active_repo)
    state_path = active_repo / state_mod.STATE_PATH
    rev = state_mod.load(state_path).harness_rev
    state_path.write_text("{not json", encoding="utf-8")
    seed = active_repo.parent / "seed"
    commit(seed, "more pay", {"svc/pay/pay/new.py": "z = 1\n"}, date="2026-03-02T00:00:00Z", author="A")
    subprocess.run(["git", "push", "-q", str(active_repo.parent / "origin.git"), "main"], cwd=seed, check=True)
    subprocess.run(["git", "fetch", "-q", "origin"], cwd=active_repo, check=True)
    assert main(["apply", str(active_repo), "--dry-run"]) == 1  # apply still refuses the stale plan
    assert "run `sherpa plan` first" in capsys.readouterr().err
    assert main(["adopt", str(active_repo)]) == 0
    out, err = capsys.readouterr()
    assert "`sherpa adopt` rebuilds it" in err and "is now at" not in err and " kept" in out
    assert state_mod.load(state_path).harness_rev == rev
    # the other way round works too: plan survives the torn index and reports it
    state_path.write_text("{not json", encoding="utf-8")
    assert main(["plan", str(active_repo)]) == 0
    assert "`sherpa adopt` rebuilds it" in capsys.readouterr().err
    assert main(["adopt", str(active_repo)]) == 0
    assert main(["apply", str(active_repo), "--yes"]) == 0


# ---------------------------------------------------------------- ADR-0049: a nested AGENTS.md covers by path


def _entry(kind: str, target: str, scope: str, **kw) -> Entry:
    return Entry(kind, target, scope, PROPOSE, {}, (), "", **kw)


def test_covers_by_path_only_a_hand_written_nested_agents_md():
    """The exact-match rule: the unit's own AGENTS.md, hand-written (no sherpa markers), nothing decided yet."""
    plan = Plan(
        "r",
        {},
        {},
        {},
        [
            _entry("owner-doc", "pay", "svc/pay"),
            _entry("owner-doc", "rootmod", ""),
            _entry("test-infra", "suite", "tests/suite"),
            _entry("owner-doc", "decided", "svc/decided", decision="accept"),
            _entry("owner-doc", "hand", "svc/hand", covered="docs/own.md"),
            _entry("owner-doc", "managed", "svc/managed"),
            _entry("owner-doc", "again", "svc/again", covered="svc/again/AGENTS.md"),
            _entry("owner-doc", "applied", "svc/applied", covered="svc/applied/AGENTS.md"),
            _entry("owner-doc", "rebuilt", "svc/rebuilt"),
        ],
    )
    block = "<!-- sherpa:begin facts -->\nfacts\n<!-- sherpa:end facts -->\n"
    found_files = [
        found("svc/pay/AGENTS.md", "# pay\n"),  # the unit's own file: covers
        found("svc/again/AGENTS.md", "# a\n"),  # covered by this very path already: covers again, every run
        replace(found("svc/applied/AGENTS.md", block), markers=True),  # same, after `apply` appended its block
        replace(found("svc/rebuilt/AGENTS.md", f"# r\n\n{block}"), markers=True),  # prose of its own: the team's
        found("AGENTS.md", "# root\n"),  # the harness index: covers nothing
        found("svc/pay/CLAUDE.md", "# claude\n"),  # runtime-specific: covers nothing
        found("tests/suite/AGENTS.md", "# suite\n"),  # a test-infra unit's own file: covers
        found("svc/decided/AGENTS.md", "# d\n"),  # the team decided the entry itself
        found("svc/hand/AGENTS.md", "# h\n"),  # a hand-written covered: stands
        replace(found("svc/managed/AGENTS.md", block), markers=True),  # nothing but sherpa's block: sherpa's own
    ]
    assert covers_by_path(plan, found_files) == {
        "owner-doc:pay:svc/pay": "svc/pay/AGENTS.md",
        "test-infra:suite:tests/suite": "tests/suite/AGENTS.md",
        "owner-doc:again:svc/again": "svc/again/AGENTS.md",
        "owner-doc:applied:svc/applied": "svc/applied/AGENTS.md",
        "owner-doc:rebuilt:svc/rebuilt": "svc/rebuilt/AGENTS.md",
    }
    assert own_prose("<!-- sherpa:begin x -->\nno end\n") == "", "broken markers are not a doc"


def test_adopt_covers_a_unit_whose_own_path_has_an_agents_md(active_repo: Path, capsys):
    """ADR-0049: the team's own AGENTS.md at the unit's path is the owner doc — recorded on the entry, kept
    across a re-plan like a hand-written `covered:`, dropped and named when the file vanishes."""
    (active_repo / "svc/pay/AGENTS.md").write_text("# pay\n\nOur payment module.\n", encoding="utf-8")
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    before = tree_hash(active_repo)
    assert main(["adopt", str(active_repo)]) == 0
    out = capsys.readouterr().out
    assert tree_hash(active_repo) == before, "adopt changed a harness file"
    assert "· svc/pay/AGENTS.md" in out
    assert "covers owner-doc pay (the unit's own path) — `apply` appends its facts block" in out
    assert "2 proposed owner docs without an existing doc" in out  # pay is covered; core and suite are not
    plan_path = active_repo / ".sherpa/harness-plan.yaml"
    plan = yamlio.plan_from_dict(yamlio.load(plan_path))
    assert {e.address: e for e in plan.entries}["owner-doc:pay:svc/pay"].covered == "svc/pay/AGENTS.md"
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    plan = yamlio.plan_from_dict(yamlio.load(plan_path))
    assert {e.address: e for e in plan.entries}["owner-doc:pay:svc/pay"].covered == "svc/pay/AGENTS.md"
    (active_repo / "svc/pay/AGENTS.md").unlink()
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    assert "was covered by svc/pay/AGENTS.md, which no longer exists — dropped" in capsys.readouterr().out


def test_adopt_is_the_same_on_the_second_run_and_after_apply(active_repo: Path, capsys):
    """A cover by path is the same fact on every run: the second `adopt` (the plan now carries the `covered:`)
    prints the same rows and gaps and records the same state as the first, and so does the one after `apply`
    appended its facts block — the hand-written doc at sherpa's path stays yours and never regains the entry."""
    existing_harness(active_repo)  # .claude/docs/modules/pay.md would link by name
    (active_repo / "svc/pay/AGENTS.md").write_text("# pay\n\nOurs.\n", encoding="utf-8")
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    capsys.readouterr()

    def run() -> tuple[str, str, dict]:
        assert main(["adopt", str(active_repo)]) == 0
        out = capsys.readouterr().out
        state = state_mod.load(active_repo / state_mod.STATE_PATH)
        return out, out[out.index("gaps:") :].split("state:")[0], {p: r.entry for p, r in state.files.items()}

    first, gaps, entries = run()
    assert entries[".claude/docs/modules/pay.md"] is None
    assert "svc/pay/AGENTS.md covers it (the unit's own path)" in first
    assert "covers owner-doc pay (the unit's own path)" in first
    assert "2 proposed owner docs without an existing doc" in gaps
    second, gaps2, entries2 = run()  # the plan now carries the `covered:` — the wording moves, the facts do not
    assert (gaps2, entries2) == (gaps, entries), "the second adopt differs from the first"
    assert "svc/pay/AGENTS.md covers it (the unit's own path)" in second
    assert "covers owner-doc pay (the unit's own path)" in second
    assert main(["apply", str(active_repo), "--yes"]) == 0
    capsys.readouterr()
    after, gaps3, entries3 = run()
    assert entries3[".claude/docs/modules/pay.md"] is None
    assert "svc/pay/AGENTS.md covers it (the unit's own path)" in after
    assert "pay.md: no unit matches" not in after and "proposed owner doc" not in gaps3
    plan = yamlio.plan_from_dict(yamlio.load(active_repo / ".sherpa/harness-plan.yaml"))
    assert {e.address: e for e in plan.entries}["owner-doc:pay:svc/pay"].covered == "svc/pay/AGENTS.md"


def test_a_hand_written_covered_stands_against_a_by_path_cover(active_repo: Path, capsys):
    """ADR-0046 beats ADR-0049: the plan's own word is never overridden by the path rule."""
    (active_repo / "docs").mkdir()
    (active_repo / "docs/pay.md").write_text("# pay — ours\n", encoding="utf-8")
    (active_repo / "svc/pay/AGENTS.md").write_text("# pay\n", encoding="utf-8")
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    plan_path = active_repo / ".sherpa/harness-plan.yaml"
    plan = yamlio.plan_from_dict(yamlio.load(plan_path))
    plan = replace(
        plan,
        entries=[
            replace(e, covered="docs/pay.md") if e.address == "owner-doc:pay:svc/pay" else e for e in plan.entries
        ],
    )
    yamlio.write(plan, plan_path)
    assert main(["adopt", str(active_repo)]) == 0
    out = capsys.readouterr().out
    assert "covers owner-doc pay (the unit's own path)" not in out
    assert "· svc/pay/AGENTS.md" in out and "no sherpa markers — `apply` appends its block" in out
    plan = yamlio.plan_from_dict(yamlio.load(plan_path))
    assert {e.address: e for e in plan.entries}["owner-doc:pay:svc/pay"].covered == "docs/pay.md"


def test_a_by_path_cover_beats_a_doc_at_sherpas_path(active_repo: Path, capsys):
    """A hand-written owner doc at sherpa's own path loses to the unit's own AGENTS.md — the file stays the
    team's, linked to nothing, and the row says why. `plan` sets the cover itself (no `adopt` needed before
    `apply`); on a plan an older sherpa wrote without it, `adopt` finds the same cover and says so. With the
    claude target only, the facts land in the nested CLAUDE.md and the row names it."""
    existing_harness(active_repo)  # .claude/docs/modules/pay.md is hand-written and would cover the entry
    (active_repo / "svc/pay/AGENTS.md").write_text("# pay\n\nOurs.\n", encoding="utf-8")
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    assert "(1 covered by existing files)" in capsys.readouterr().out
    plan_path = active_repo / ".sherpa/harness-plan.yaml"
    plan = yamlio.plan_from_dict(yamlio.load(plan_path))
    assert {e.address: e for e in plan.entries}["owner-doc:pay:svc/pay"].covered == "svc/pay/AGENTS.md"
    assert main(["adopt", str(active_repo)]) == 0
    out = capsys.readouterr().out
    assert "a .claude/docs/modules/pay.md" in out
    assert "matches owner-doc pay (name matches) — yours, svc/pay/AGENTS.md covers it (the unit's own path)" in out
    assert "covers owner-doc pay (the unit's own path) — the facts go to svc/pay/CLAUDE.md" in out
    state = state_mod.load(active_repo / state_mod.STATE_PATH)
    assert state.files[".claude/docs/modules/pay.md"].entry is None
    # a plan from before ADR-0049: the doc at sherpa's path is rendered, and still loses to the unit's own file
    yamlio.write(replace(plan, entries=[replace(e, covered=None) for e in plan.entries]), plan_path)
    assert main(["adopt", str(active_repo)]) == 0
    out = capsys.readouterr().out
    assert "at sherpa's path, yours — svc/pay/AGENTS.md covers it (the unit's own path)" in out
    plan = yamlio.plan_from_dict(yamlio.load(plan_path))
    assert {e.address: e for e in plan.entries}["owner-doc:pay:svc/pay"].covered == "svc/pay/AGENTS.md"
    assert state_mod.load(active_repo / state_mod.STATE_PATH).files[".claude/docs/modules/pay.md"].entry is None
    assert main(["apply", str(active_repo), "--yes"]) == 0
    assert not (active_repo / ".claude/docs/modules/pay.md").read_text(encoding="utf-8").count("sherpa:begin")
    nested = (active_repo / "svc/pay/CLAUDE.md").read_text(encoding="utf-8")
    assert "sherpa:begin harness" in nested and "Read the owner doc [svc/pay/AGENTS.md](AGENTS.md)" in nested
    assert "sherpa:" not in (active_repo / "svc/pay/AGENTS.md").read_text(encoding="utf-8"), "no agents-md target"


def test_a_by_path_cover_beats_a_name_link(active_repo: Path, capsys):
    """The name/mention heuristic loses to the unit's own AGENTS.md (here on a skipped entry, whose doc path
    is not rendered): the doc stays the team's, unlinked, and the row names the cover."""
    doc = active_repo / ".agents/docs/modules/web.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("# web — our notes on svc/web\n", encoding="utf-8")
    (active_repo / "svc/web/AGENTS.md").write_text("# web\n", encoding="utf-8")
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    assert main(["adopt", str(active_repo)]) == 0
    out = capsys.readouterr().out
    assert "matches owner-doc web (name matches) — yours, svc/web/AGENTS.md covers it (the unit's own path)" in out
    state = state_mod.load(active_repo / state_mod.STATE_PATH)
    assert state.files[".agents/docs/modules/web.md"].entry is None


def test_an_ignored_agents_md_covers_nothing(active_repo: Path, capsys):
    """A git-ignored file is not the harness — it is not even seen, so it covers nothing."""
    (active_repo / "svc/pay/AGENTS.md").write_text("# pay\n", encoding="utf-8")
    (active_repo / ".gitignore").write_text("svc/pay/AGENTS.md\n", encoding="utf-8")
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    assert main(["adopt", str(active_repo)]) == 0
    assert "svc/pay/AGENTS.md" not in capsys.readouterr().out
    plan = yamlio.plan_from_dict(yamlio.load(active_repo / ".sherpa/harness-plan.yaml"))
    assert {e.address: e for e in plan.entries}["owner-doc:pay:svc/pay"].covered is None


def test_apply_after_a_by_path_cover_writes_no_skeleton(active_repo: Path, capsys):
    """The F39 flow, `plan` → `apply` with no `adopt` in between: the team's own svc/pay/AGENTS.md is the owner
    doc — apply writes the facts block into it and no skeleton under docs/modules/; agents point at the unit's
    own file; the second run is all `=`. A lost `.sherpa/` rebuilds the cover from the files (ADR-0017): the
    file has prose of its own outside sherpa's block, so plan, adopt and apply agree again — nothing to do."""
    (active_repo / "svc/pay/AGENTS.md").write_text("# pay\n\nOur payment module.\n", encoding="utf-8")
    applied(active_repo)
    assert "check: 0 FAIL" in capsys.readouterr().out
    assert not (active_repo / ".agents/docs/modules/pay.md").exists(), "no skeleton next to the team's doc"
    assert (active_repo / ".agents/docs/modules/core.md").exists(), "uncovered units keep their owner doc"
    agents_md = (active_repo / "svc/pay/AGENTS.md").read_text(encoding="utf-8")
    assert agents_md.startswith("# pay\n\nOur payment module.\n"), "the team's prose stays"
    assert "sherpa:begin facts" in agents_md
    assert "Read the owner doc" not in agents_md, "the file is the owner doc — no pointer to itself"
    agent = (active_repo / ".claude/agents/pay.md").read_text(encoding="utf-8")
    assert "../../svc/pay/AGENTS.md" in agent  # knowledge manifest and "Read first" point at the unit's file
    assert ".agents/docs/modules/pay.md" not in agent
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    assert "nothing to do." in capsys.readouterr().out
    shutil.rmtree(active_repo / ".sherpa")
    before = tree_hash(active_repo)
    applied(active_repo)  # plan finds the cover in the file itself; apply has nothing to write
    assert main(["adopt", str(active_repo)]) == 0
    out = capsys.readouterr().out
    assert tree_hash(active_repo) == before, "the rebuilt index changed a harness file"
    assert "svc/pay/AGENTS.md" in out and "1 of 1 blocks match the plan; covers owner-doc pay" in out
    assert "hand edit" not in out and "gaps:" not in out
    assert not (active_repo / ".agents/docs/modules/pay.md").exists()


def test_an_agent_seeded_by_an_older_sherpa_is_still_sherpas_whole(active_repo: Path, capsys):
    """ADR-0022 for prose outside the markers: the Role line sherpa ≤ 0.7.7 seeded named the owner doc by path.
    After a state rebuild the file must still count as sherpa's whole — otherwise `apply --remove` would cut
    the blocks and leave the seed behind (ADR-0048)."""
    applied(active_repo)
    agent = active_repo / ".claude/agents/pay.md"
    text = agent.read_text(encoding="utf-8")
    old = text.replace(
        "they live\n> in the owner doc named in the knowledge manifest; cite",
        "they live in\n> [.agents/docs/modules/pay.md](../../.agents/docs/modules/pay.md); cite",
    )
    assert old != text
    agent.write_text(old, encoding="utf-8")
    (active_repo / state_mod.STATE_PATH).unlink()
    assert main(["adopt", str(active_repo)]) == 0
    assert "= .claude/agents/pay.md" in capsys.readouterr().out
    rec = state_mod.load(active_repo / state_mod.STATE_PATH).files[".claude/agents/pay.md"]
    assert rec.origin == GENERATED and rec.hash is not None, "sherpa's whole, up to the older seed"
    assert main(["apply", str(active_repo), "--yes"]) == 0
    assert agent.read_text(encoding="utf-8") == text, "apply refreshes the seed"
    assert main(["apply", str(active_repo), "--remove", "--yes"]) == 0
    assert not agent.exists()


def test_a_hand_cover_on_an_applied_unit_takes_the_skeleton_back(active_repo: Path, capsys):
    """ADR-0048 meets ADR-0049: a `covered:` on an already-applied unit — the skeleton is sherpa's and
    unchanged, so apply takes it back; the team's file keeps the facts block; nothing links into the void."""
    applied(active_repo)
    skeleton = active_repo / ".agents/docs/modules/pay.md"
    assert skeleton.exists()
    plan_path = active_repo / ".sherpa/harness-plan.yaml"
    plan = yamlio.plan_from_dict(yamlio.load(plan_path))
    plan = replace(
        plan,
        entries=[
            replace(e, covered="svc/pay/AGENTS.md") if e.address == "owner-doc:pay:svc/pay" else e for e in plan.entries
        ],
    )
    yamlio.write(plan, plan_path)
    assert main(["apply", str(active_repo), "--yes"]) == 0
    out = capsys.readouterr().out
    assert "removed (no longer in the plan)" in out and "check: 0 FAIL" in out
    assert not skeleton.exists()
    agents_md = (active_repo / "svc/pay/AGENTS.md").read_text(encoding="utf-8")
    assert "sherpa:begin facts" in agents_md and "Read the owner doc" not in agents_md
    agent = (active_repo / ".claude/agents/pay.md").read_text(encoding="utf-8")
    assert "../../svc/pay/AGENTS.md" in agent and ".agents/docs/modules/pay.md" not in agent
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    assert "nothing to do." in capsys.readouterr().out


def test_adopt_by_path_cover_golden(active_repo: Path, capsys):
    """§13.3: the cover by path on the five-module fixture — the console view is the golden."""
    (active_repo / "svc/pay/AGENTS.md").write_text("# pay\n\nOur payment module.\n", encoding="utf-8")
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    capsys.readouterr()
    assert main(["adopt", str(active_repo)]) == 0
    check_golden("active-adopt-bypath-console.txt", capsys.readouterr().out)
