"""``sherpa apply`` takes its own bytes back (ADR-0048): a rejected entry, a unit gone from the trunk, the uninstall."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from sherpa.apply import state as state_mod
from sherpa.cli import main
from tests.conftest import commit
from tests.test_apply import applied, tree_hash


def _git_status(repo: Path) -> set[str]:
    """``git status --ignored --porcelain``: tracked changes, untracked and ignored files — the acceptance of
    ADR-0048 is that apply + remove leave it as it was."""
    args = ["git", "status", "--ignored", "--porcelain"]
    out = subprocess.run(args, cwd=repo, capture_output=True, text=True, check=True).stdout
    return {line[3:] for line in out.splitlines()}


def test_reject_after_apply_removes_the_agent_and_keeps_a_hand_edited_one(active_repo: Path, capsys):
    applied(active_repo)
    agent = active_repo / ".claude" / "agents" / "pay.md"
    doc = active_repo / ".agents" / "docs" / "modules" / "pay.md"
    assert agent.is_file() and doc.is_file()
    assert main(["plan", str(active_repo), "--no-fetch", "--reject", "agent:pay", "--reject", "owner-doc:pay"]) == 0
    doc.write_text(doc.read_text(encoding="utf-8") + "\nMy own paragraph.\n", encoding="utf-8")  # a hand edit
    capsys.readouterr()
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "  - .claude/agents/pay.md" in out and "removed (no longer in the plan)" in out
    assert "  - .agents/docs/modules/pay.md" in out and "block facts removed (no longer in the plan)" in out
    assert "  - svc/pay/AGENTS.md" in out and "  - svc/pay/CLAUDE.md" in out and "4 to remove." in out
    assert agent.is_file(), "the dry run removes nothing"
    assert main(["apply", str(active_repo), "--yes"]) == 0
    out = capsys.readouterr().out
    assert "3 removed · harness_rev" in out and "check: 0 FAIL" in out
    assert not agent.exists() and not (active_repo / "svc" / "pay" / "AGENTS.md").exists()
    text = doc.read_text(encoding="utf-8")  # the hand-edited doc keeps the hand's text, loses sherpa's block
    assert doc.is_file() and "My own paragraph." in text and "sherpa:begin" not in text
    files = state_mod.load(active_repo / state_mod.STATE_PATH).files
    assert ".claude/agents/pay.md" not in files and ".agents/docs/modules/pay.md" not in files
    # idempotent: the second run has nothing to remove, and status is clean
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "to remove" not in out and "pay.md" not in out.split("\n", 2)[2].replace("svc/pay/", "")
    assert main(["status", str(active_repo)]) == 0
    assert "drift: none" in capsys.readouterr().out
    # a rollback restores a removed file: make the removal introduce a FAIL (an agent whose owner doc goes)
    assert main(["plan", str(active_repo), "--no-fetch", "--accept", "agent:pay"]) == 0
    assert main(["apply", str(active_repo), "--yes"]) == 0
    capsys.readouterr()


def test_a_unit_gone_from_the_trunk_takes_its_files_with_it(active_repo: Path, capsys):
    applied(active_repo)
    before = tree_hash(active_repo)
    seed = active_repo.parent / "seed"
    subprocess.run(["git", "rm", "-rq", "svc/core"], cwd=seed, check=True)
    commit(seed, "drop core", {}, date="2026-03-02T00:00:00Z", author="A")
    subprocess.run(["git", "push", "-q", str(active_repo.parent / "origin.git"), "main"], cwd=seed, check=True)
    subprocess.run(["git", "fetch", "-q", "origin"], cwd=active_repo, check=True)
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    capsys.readouterr()
    assert main(["apply", str(active_repo), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert (
        "  - .agents/docs/modules/core.md" in out
        and "  - svc/core/AGENTS.md" in out
        and "  - svc/core/CLAUDE.md" in out
    )
    assert main(["apply", str(active_repo), "--yes"]) == 0
    out = capsys.readouterr().out
    assert "3 removed" in out and "check: 0 FAIL" in out
    assert not (active_repo / ".agents" / "docs" / "modules" / "core.md").exists()
    assert not (active_repo / "svc" / "core" / "AGENTS.md").exists()
    assert tree_hash(active_repo) != before
    assert main(["status", str(active_repo)]) == 0
    assert "drift: none" in capsys.readouterr().out


def test_remove_is_the_uninstall_and_leaves_only_what_is_yours(active_repo: Path, capsys):
    """Acceptance (plan §3, M3i): `apply` + `apply --remove` on a clean repository leave `git status --ignored`
    as it was — merged JSON keys, appended blocks, the index and the telemetry included; with hand edits it
    keeps exactly those files and blocks and says so."""
    (active_repo / "CLAUDE.md").write_text("# Shop\n\nHand-written.\n", encoding="utf-8")
    settings = active_repo / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps({"permissions": {"allow": ["Bash(ls)"]}}, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", "CLAUDE.md", ".claude/settings.json"], cwd=active_repo, check=True)
    subprocess.run(["git", "commit", "-qm", "theirs"], cwd=active_repo, check=True)
    clean = _git_status(active_repo)
    applied(active_repo)
    (active_repo / ".sherpa" / "telemetry" / "outcomes.ndjson").write_text('{"kind": "outcome"}\n', encoding="utf-8")
    assert "sherpa:begin harness" in (active_repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert "sherpa-outcome.py" in settings.read_text(encoding="utf-8")
    assert _git_status(active_repo) > clean
    capsys.readouterr()
    assert main(["apply", str(active_repo), "--remove", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "  - CLAUDE.md" in out and "block harness removed (--remove)" in out
    assert "hooks removed: UserPromptSubmit, PostToolUse, PostToolUseFailure, Stop (--remove)" in out
    assert "  - .claude/scripts/sherpa-check.py" in out and "  - .sherpa/telemetry/.gitignore" in out
    assert "0 to add, 0 to change, 0 unchanged, 0 skipped, 13 to remove." in out
    assert (active_repo / ".sherpa" / "state.json").is_file(), "the dry run removes nothing"
    assert main(["apply", str(active_repo), "--remove", "--yes"]) == 0
    out = capsys.readouterr().out
    assert "2 files written, 11 removed · harness_rev" in out and "check: 0 FAIL" in out
    assert (
        "uninstalled — .sherpa/state.json, .sherpa/harness-plan.yaml, .sherpa/codebase-model.json, "
        ".sherpa/telemetry/outcomes.ndjson removed too" in out
    )
    assert (active_repo / "CLAUDE.md").read_text(encoding="utf-8") == "# Shop\n\nHand-written.\n"
    assert json.loads(settings.read_text(encoding="utf-8")) == {"permissions": {"allow": ["Bash(ls)"]}}
    assert not (active_repo / ".claude" / "agents").exists() and not (active_repo / ".claude" / "docs").exists()
    assert not (active_repo / "svc" / "pay" / "AGENTS.md").exists()
    assert _git_status(active_repo) == clean, "apply + remove leave git status --ignored as it was"
    assert (active_repo / ".sherpa").exists() is False
    # with a hand edit: the edited block stays, the file with it, and the console says what is yours
    applied(active_repo)
    nested = active_repo / "svc" / "pay" / "CLAUDE.md"
    nested.write_text(nested.read_text(encoding="utf-8").replace("| unit |", "| UNIT |"), encoding="utf-8")
    capsys.readouterr()
    assert main(["apply", str(active_repo), "--remove", "--yes"]) == 0
    out = capsys.readouterr().out
    assert "  ! svc/pay/CLAUDE.md" in out and "block harness hand-edited — yours now (kept)" in out
    assert "kept, yours: svc/pay/CLAUDE.md" in out and "uninstalled —" in out
    assert nested.is_file() and "| UNIT |" in nested.read_text(encoding="utf-8")
    assert not (active_repo / "svc" / "core" / "CLAUDE.md").exists()
    assert _git_status(active_repo) == clean | {"svc/pay/CLAUDE.md"}


def test_adopt_records_a_leftover_of_a_deselected_entry_as_sherpas_not_yours(active_repo: Path, capsys):
    """§11 F25: reject an applied agent, lose the state, rebuild it — the rejected agent's file is sherpa's
    leftover (an orphan record `apply` removes), never adopted as yours and never a cover on the rejected entry."""
    applied(active_repo)
    assert main(["plan", str(active_repo), "--no-fetch", "--reject", "agent:pay"]) == 0
    (active_repo / state_mod.STATE_PATH).unlink()  # a lost state (a merge conflict resolved the wrong way)
    capsys.readouterr()
    assert main(["adopt", str(active_repo)]) == 0
    out = capsys.readouterr().out
    assert "= .claude/agents/pay.md" in out and "sherpa's, no longer in the plan — `apply` removes it" in out
    assert "a .claude/agents/pay.md" not in out and "covers the entry" not in out.split("pay.md")[0]
    files = state_mod.load(active_repo / state_mod.STATE_PATH).files
    assert files[".claude/agents/pay.md"].origin == "generated" and files[".claude/agents/pay.md"].entry
    plan_text = (active_repo / ".sherpa" / "harness-plan.yaml").read_text(encoding="utf-8")
    assert "covered: .claude/agents/pay.md" not in plan_text
    assert main(["plan", str(active_repo), "--no-fetch"]) == 0
    assert "[reject]" in capsys.readouterr().out and "[covered by .claude/agents/pay.md]" not in plan_text
    assert main(["apply", str(active_repo), "--yes"]) == 0
    assert "1 removed" in capsys.readouterr().out and not (active_repo / ".claude" / "agents" / "pay.md").exists()
