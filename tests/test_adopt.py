"""``sherpa adopt``: classification, linking, covering plan entries, never touching a byte, rebuilding a lost state."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from sherpa import atomic
from sherpa.apply import state as state_mod
from sherpa.apply.adopt import Found, kind_of, link
from sherpa.apply.render import selected
from sherpa.apply.state import ADOPTED, GENERATED
from sherpa.cli import main
from sherpa.plan import yamlio
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
    assert "2 covered by adopted files" in capsys.readouterr().out
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


def test_adopt_rebuilds_a_lost_or_torn_state(active_repo: Path, capsys):
    applied(active_repo)
    state_path = active_repo / state_mod.STATE_PATH
    rev = state_mod.load(state_path).harness_rev
    before = tree_hash(active_repo)
    state_path.write_text('{"schema_version": 1, "files": {', encoding="utf-8")  # torn write
    assert main(["status", str(active_repo)]) == 1
    assert "`sherpa adopt` rebuilds it from the harness files" in capsys.readouterr().err
    assert main(["adopt", str(active_repo)]) == 0
    out, err = capsys.readouterr()
    assert "rebuilding" in err and "0 adopted" in out and " kept" in out
    state = state_mod.load(state_path)
    assert all(r.origin == GENERATED for r in state.files.values())
    assert state.harness_rev == rev, "the rebuilt state is the one apply wrote"
    assert tree_hash(active_repo) == before
    assert main(["apply", str(active_repo), "--yes"]) == 0
    assert "nothing to do." in capsys.readouterr().out
    # second adopt keeps every record (hashes match) and writes the same state again
    assert main(["adopt", str(active_repo)]) == 0
    assert f"0 adopted, 0 rebuilt, {len(state.files)} kept, 0 dropped" in capsys.readouterr().out


def test_adopt_keeps_hand_edits_and_refreshes_base_files_by_name(active_repo: Path, capsys):
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
    assert "= .agents/scripts/sherpa-check.py" in out and "sherpa's by name — `apply` refreshes it" in out
    state = state_mod.load(active_repo / state_mod.STATE_PATH)
    assert state.files["svc/pay/AGENTS.md"].blocks == {}
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "! svc/pay/AGENTS.md" in out and "block facts not written by sherpa" in out
    assert "~ .agents/scripts/sherpa-check.py" in out


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
    assert out.endswith("harness-plan.yaml (2 covered by adopted files)\n")
    check_golden("active-plan-covered-console.txt", out[: out.rindex("→ ")])
