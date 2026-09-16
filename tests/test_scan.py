"""Ende-zu-Ende: scan(), Determinismus, Konfig, Schema, CLI."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from sherpa import __version__
from sherpa.cli import EXIT_ERROR, EXIT_NOT_IMPLEMENTED, EXIT_OK, main
from sherpa.model import validate
from sherpa.scan import parse_as_of, scan
from tests.conftest import commit, git


@pytest.fixture
def clone(make_origin, make_clone) -> Path:
    origin, _ = make_origin(("main", "dev"))
    return make_clone(origin)


def test_scan_is_deterministic(clone: Path):
    a = scan(clone, fetch=False).to_json()
    b = scan(clone, fetch=False).to_json()
    assert a == b
    assert a.endswith("\n")


def test_scan_ignores_local_branch_and_worktree(clone: Path):
    before = scan(clone, fetch=False).to_json()
    git(clone, "checkout", "-q", "-b", "task/x")
    commit(clone, "local", {"z.txt": "z\n"})
    (clone / "dirty.txt").write_text("dirty")
    assert scan(clone, fetch=False).to_json() == before


def test_scan_validates_against_schema(clone: Path):
    validate(asdict(scan(clone, fetch=False)))


def test_scan_model_header(clone: Path):
    m = scan(clone, fetch=False)
    assert (m.sherpa, m.schema_version, m.repo) == (__version__, 2, "clone")
    assert m.origin.endswith("origin.git")
    assert m.git.trunk.ref == "origin/main"


def test_scan_trunk_from_config(clone: Path):
    (clone / "sherpa.toml").write_text('[scan]\ntrunk = "dev"\nhotspots = 1\n')
    m = scan(clone, fetch=False)
    assert m.git.trunk == m.git.trunk.__class__("origin/dev", "override", m.git.trunk.rev)
    assert len(m.git.hotspots) <= 1


def test_scan_generated_from_config(clone: Path):
    (clone / "sherpa.toml").write_text('[scan]\ngenerated = ["f.txt"]\n')
    m = scan(clone, fetch=False)
    assert {f.path: f.generated for f in m.git.files} == {"f.txt": True}
    assert m.git.hotspots == []


def test_scan_cli_arg_beats_config(clone: Path):
    (clone / "sherpa.toml").write_text('[scan]\ntrunk = "dev"\n')
    assert scan(clone, trunk="main", fetch=False).git.trunk.ref == "origin/main"


def test_scan_fetch_picks_up_upstream(clone: Path, tmp_path: Path):
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(tmp_path / "origin.git"), str(other))
    new = commit(other, "up", {"u.txt": "u\n"})
    git(other, "push", "-q", "origin", "main")
    assert scan(clone, fetch=False).git.trunk.rev != new
    assert scan(clone, fetch=True).git.trunk.rev == new


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2026-03-01", "2026-03-01T00:00:00+00:00"),
        ("2026-03-01T10:00:00", "2026-03-01T10:00:00+00:00"),
        ("2026-03-01T10:00:00+02:00", "2026-03-01T08:00:00+00:00"),
    ],
)
def test_parse_as_of(value, expected):
    assert parse_as_of(value).isoformat() == expected


def test_cli_scan_writes_model(clone: Path, capsys):
    assert main(["scan", str(clone), "--no-fetch"]) == EXIT_OK
    out = clone / ".sherpa" / "codebase-model.json"
    data = json.loads(out.read_text())
    validate(data)
    assert data["git"]["trunk"]["ref"] == "origin/main"
    assert "→" in capsys.readouterr().err


def test_cli_scan_stdout_and_as_of(clone: Path, capsys):
    assert main(["scan", str(clone), "--no-fetch", "--out", "-", "--as-of", "2030-01-01", "--top", "3"]) == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["git"]["windows"]["as_of"] == "2030-01-01T00:00:00Z"
    assert data["git"]["commits_90d"] == 0


def test_cli_scan_custom_out(clone: Path, tmp_path: Path):
    target = tmp_path / "x" / "m.json"
    assert main(["scan", str(clone), "--no-fetch", "--out", str(target)]) == EXIT_OK
    assert target.exists()


def test_cli_scan_errors_exit_1(tmp_path: Path, capsys):
    assert main(["scan", str(tmp_path), "--no-fetch"]) == EXIT_ERROR
    assert "kein Git-Repo" in capsys.readouterr().err
    assert main(["scan", str(tmp_path), "--no-fetch", "--as-of", "gestern"]) == EXIT_ERROR


def test_cli_scan_bad_trunk_exit_1(clone: Path, capsys):
    assert main(["scan", str(clone), "--no-fetch", "--trunk", "release"]) == EXIT_ERROR
    assert "existiert nicht" in capsys.readouterr().err


def test_cli_other_commands_unimplemented():
    for cmd in ("plan", "apply", "status"):
        assert main([cmd]) == EXIT_NOT_IMPLEMENTED
