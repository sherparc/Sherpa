"""End to end: scan(), determinism, config, schema, CLI."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from sherpa import __version__
from sherpa.cli import EXIT_ERROR, EXIT_OK, main
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
    assert (m.sherpa, m.schema_version, m.repo) == (__version__, 5, "clone")
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
    assert "is not a git repository" in capsys.readouterr().err
    assert main(["scan", str(tmp_path), "--no-fetch", "--as-of", "gestern"]) == EXIT_ERROR


def test_cli_scan_bad_trunk_exit_1(clone: Path, capsys):
    assert main(["scan", str(clone), "--no-fetch", "--trunk", "release"]) == EXIT_ERROR
    assert "does not exist" in capsys.readouterr().err


def test_cli_adopt_needs_a_plan(tmp_path: Path, capsys):
    assert main(["adopt", str(tmp_path)]) == 1
    assert "run `sherpa plan` first" in capsys.readouterr().err


def test_scan_counts_churn_on_non_ascii_tab_and_newline_paths(tmp_path: Path):
    """ADR-0038: ``git log --name-only`` C-quotes unusual paths (``"\\303\\274ber.py"``) unless ``-z`` — such a
    path never matched ``ls-tree -z`` and lost its churn, so hotspots and authors were wrong wherever a file name
    holds an umlaut, CJK or a control character."""
    from datetime import UTC, datetime

    from sherpa.scan.t0_git import Trunk, collect, log_since

    seed = tmp_path / "seed"
    seed.mkdir()
    git(seed, "init", "-q", "-b", "main")
    names = {"normal.py": "x = 1\n", "über.py": "y = 1\n", "日本.py": "z = 1\n"}
    control = (
        sys.platform != "win32"
    )  # NTFS refuses tab and newline in a file name; the umlauts still exercise the C-quoting
    if control:
        names |= {"tab\tname.py": "t = 1\n", "new\nline.py": "n = 1\n"}
    commit(seed, "one", names, date="2026-03-01T00:00:00Z", author="A")
    commit(seed, "two", {k: v + "# more\n" for k, v in names.items()}, date="2026-03-02T00:00:00Z", author="B")
    origin = tmp_path / "origin.git"
    git(tmp_path, "clone", "-q", "--bare", str(seed), str(origin))
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(origin), str(clone))

    commits = log_since(clone, "origin/main", datetime(2026, 1, 1, tzinfo=UTC))
    assert len(commits) == 2 and all(c.files == tuple(sorted(names)) for c in commits)
    rev = git(clone, "rev-parse", "origin/main")
    data = collect(clone, Trunk("origin/main", "origin/HEAD", rev))
    per_file = {f: sum(1 for c in data.commits if f in c.files) for f in names}
    assert per_file == dict.fromkeys(names, 2)
    model = scan(clone, fetch=False)
    hot = {h.path: h.commits_90d for h in model.git.hotspots}
    assert hot["über.py"] == 2 and hot["日本.py"] == 2 and hot["normal.py"] == 2
    if control:
        assert hot["tab\tname.py"] == 2
        assert "new\nline.py" not in hot, (
            "no LOC for a path with a newline (cat-file --batch is line-based), no hotspot"
        )
        assert hot["normal.py"] == 2, "the answers after the newline path are not shifted"
