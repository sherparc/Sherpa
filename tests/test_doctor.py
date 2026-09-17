"""``sherpa doctor``: one line per prerequisite, a fix on every problem, exit 1 only on a fail."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from sherpa import __version__, cli, doctor, update
from tests.conftest import git


def _levels(checks):
    return {c.name: c.level for c in checks}


def test_python_and_git_ok_here():
    assert doctor.check_python().level == "ok"
    g = doctor.check_git()
    assert g.level == "ok" and g.detail.startswith("git version")


def test_python_too_old(monkeypatch):
    monkeypatch.setattr(doctor.sys, "version_info", (3, 11, 4, "final", 0))
    c = doctor.check_python()
    assert c.level == "fail" and "3.12" in c.fix


def test_git_missing_or_old(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
    c = doctor.check_git()
    assert c.level == "fail" and "install git" in c.fix
    monkeypatch.setattr(doctor.shutil, "which", lambda _: "/usr/bin/git")

    class R:
        stdout = "git version 2.10.0\n"

    monkeypatch.setattr(doctor.subprocess, "run", lambda *a, **k: R())
    assert doctor.check_git().level == "warn"

    class W:
        stdout = "git version 2.45.1.windows.1\n"

    monkeypatch.setattr(doctor.subprocess, "run", lambda *a, **k: W())
    assert doctor.check_git().level == "ok"

    def boom(*a, **k):
        raise subprocess.TimeoutExpired("git", 10)

    monkeypatch.setattr(doctor.subprocess, "run", boom)
    assert doctor.check_git().level == "fail"


def test_repo_origin_trunk_on_fixture(make_origin, make_clone):
    origin, _ = make_origin()
    repo = make_clone(origin)
    assert doctor.check_repo(repo).level == "ok"
    assert doctor.check_origin(repo).level == "ok" and str(origin) in doctor.check_origin(repo).detail
    t = doctor.check_trunk(repo, None)
    assert t.level == "ok" and t.detail.startswith("origin/main @") and "origin/HEAD" in t.detail


def test_trunk_guessed_is_a_hint(make_origin, make_clone):
    origin, _ = make_origin()
    repo = make_clone(origin, set_head=False)
    t = doctor.check_trunk(repo, None)
    assert t.level == "warn" and "set-head" in t.fix


def test_trunk_missing_names_the_fix(make_origin, make_clone):
    origin, _ = make_origin(("feature",))
    repo = make_clone(origin, set_head=False)
    t = doctor.check_trunk(repo, None)
    assert t.level == "fail" and t.fix.startswith("'git remote set-head origin -a'")
    t = doctor.check_trunk(repo, "nope")
    assert t.level == "fail" and "does not exist" in t.detail


def test_not_a_repo_and_no_origin(tmp_path: Path):
    assert doctor.check_repo(tmp_path).level == "fail"
    git(tmp_path, "init", "-q")
    assert doctor.check_repo(tmp_path).level == "ok"
    c = doctor.check_origin(tmp_path)
    assert c.level == "fail" and "git remote add origin" in c.fix


def test_config_absent_valid_and_broken(tmp_path: Path):
    assert doctor.check_config(tmp_path) == (doctor.Check("sherpa.toml", "ok", "absent — defaults apply"), None)
    (tmp_path / "sherpa.toml").write_text('[scan]\ntrunk = "dev"\n')
    c, trunk = doctor.check_config(tmp_path)
    assert c.level == "ok" and trunk == "dev"
    (tmp_path / "sherpa.toml").write_text("[plan]\nbogus = 1\n")
    c, trunk = doctor.check_config(tmp_path)
    assert c.level == "fail" and "bogus" in c.detail and trunk is None


def test_runtime_detection(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
    c = doctor.check_runtime(tmp_path)
    assert c.level == "warn" and "Claude Code" in c.fix
    (tmp_path / "AGENTS.md").write_text("# x\n")
    assert doctor.check_runtime(tmp_path).level == "ok"
    monkeypatch.setattr(doctor.shutil, "which", lambda name: "/bin/" + name if name in ("claude", "codex") else None)
    c = doctor.check_runtime(tmp_path)
    assert "claude (Claude Code CLI)" in c.detail and "codex on PATH" in c.detail


def test_installer_check(monkeypatch):
    assert doctor.check_installer().detail.endswith("`git pull` updates it")
    monkeypatch.setattr(update, "installer", lambda: "uv")
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
    c = doctor.check_installer()
    assert c.level == "warn" and "not on PATH" in c.detail
    monkeypatch.setattr(doctor.shutil, "which", lambda _: "/usr/bin/uv")
    assert doctor.check_installer().level == "ok"
    monkeypatch.setattr(update, "installer", lambda: "pip")
    assert doctor.check_installer().detail.startswith(f"sherpa {__version__} via pip")


def test_update_check_states(monkeypatch):
    assert doctor.check_update().detail.startswith("check disabled")
    monkeypatch.delenv(update.NO_CHECK_ENV)
    monkeypatch.setattr(update, "token", lambda: None)
    monkeypatch.setattr(update, "latest_release", lambda tok: update.Release("99.0.0", "v99.0.0", None, ""))
    c = doctor.check_update()
    assert c.level == "warn" and c.fix == "`sherpa self-update`"
    monkeypatch.setattr(update, "latest_release", lambda tok: update.Release(__version__, "v", None, ""))
    assert doctor.check_update().level == "ok"

    def fail(tok):
        raise update.UpdateError("GitHub unreachable (x)")

    monkeypatch.setattr(update, "latest_release", fail)
    c = doctor.check_update()
    assert c.level == "warn" and "gh auth login" in c.fix


def test_run_stops_after_missing_git(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(doctor, "check_git", lambda: doctor.Check("git", "fail", "not on PATH", "install git"))
    checks = doctor.run(tmp_path)
    assert [c.name for c in checks] == ["python", "git", "install", "repository"]


def test_run_and_render_on_fixture(make_origin, make_clone):
    origin, _ = make_origin()
    repo = make_clone(origin)
    checks = doctor.run(repo)
    assert _levels(checks)["update"] == "ok"  # disabled by conftest, reported as such
    text = doctor.render(checks)
    assert text.startswith(f"sherpa doctor — {__version__}\n  ✓ python")
    assert "hints." in text or text.rstrip().endswith("ready — `sherpa plan` is the next step.")
    checks = doctor.run(repo, network=False)
    assert "update" not in _levels(checks)


def test_render_marks_fix_and_hint():
    text = doctor.render(
        [
            doctor.Check("a", "ok", "fine"),
            doctor.Check("bb", "warn", "meh", "do x"),
            doctor.Check("c", "fail", "bad", "do y"),
        ]
    )
    assert text == (
        f"sherpa doctor — {__version__}\n  ✓ a   fine\n  ! bb  meh\n    hint: do x\n"
        "  ✗ c   bad\n    fix: do y\n1 problems, 1 hints.\n"
    )


def test_render_json_is_the_same_report():
    checks = [doctor.Check("a", "ok", "fine"), doctor.Check("c", "fail", "bad", "do y")]
    j = json.loads(doctor.render_json(checks))
    assert j["sherpa"] == __version__ and j["problems"] == 1 and j["hints"] == 0
    assert j["checks"][1] == {"name": "c", "level": "fail", "detail": "bad", "fix": "do y"}


def test_cli_doctor_json(tmp_path: Path, capsys, make_origin, make_clone):
    origin, _ = make_origin()
    assert cli.main(["doctor", str(make_clone(origin)), "--offline", "--json"]) == 0
    j = json.loads(capsys.readouterr().out)
    assert j["problems"] == 0 and {c["name"] for c in j["checks"]} >= {"python", "git", "repository", "trunk"}


@pytest.mark.parametrize("args,code", [([], 1), (["--offline"], 1)])
def test_cli_doctor_exit_codes(tmp_path: Path, capsys, args, code, make_origin, make_clone):
    assert cli.main(["doctor", str(tmp_path), *args]) == code
    out = capsys.readouterr().out
    assert "✗ repository" in out and "fix:" in out
    origin, _ = make_origin()
    repo = make_clone(origin)
    assert cli.main(["doctor", str(repo), *args]) == 0
