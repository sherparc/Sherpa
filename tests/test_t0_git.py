"""T0-Scanner auf einem Fixture mit kontrollierten Daten.

Zeitachse (as_of = Committer-Datum des Trunk-Revs = 2026-03-01):
  2025-11-01  ausserhalb 90d   src/a/old.py, README.md
  2026-01-15  in 90d, nicht 30d  src/a/hot.py (Autor A), src/b/b.py
  2026-02-20  in 30d            src/a/hot.py (Autor B), bin.dat (binär)
  2026-03-01  in 30d            src/a/hot.py (Autor A)   ← Trunk-Rev
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from sherpa.gitinfo import resolve_trunk
from sherpa.config import GENERATED_DEFAULT
from sherpa.scan.t0_git import blob_locs, is_generated, list_files, log_since, scan_git
from tests.conftest import commit, git

D0, D1, D2, D3 = "2025-11-01T12:00:00Z", "2026-01-15T12:00:00Z", "2026-02-20T12:00:00Z", "2026-03-01T12:00:00Z"


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    work = tmp_path / "seed"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    commit(work, "c0", {"src/a/old.py": "x = 1\n", "README.md": "# r\n"}, date=D0, author="A")
    commit(work, "c1", {"src/a/hot.py": "a\nb\nc\n", "src/b/b.py": "b\n"}, date=D1, author="A")
    commit(work, "c2", {"src/a/hot.py": "a\nb\nc\nd\n", "bin.dat": b"\x00\x01\x02"}, date=D2, author="B")
    commit(work, "c3", {"src/a/hot.py": "a\nb\nc\nd\ne"}, date=D3, author="A")   # ohne \n am Ende → 5 LOC
    origin = tmp_path / "origin.git"
    git(tmp_path, "clone", "-q", "--bare", str(work), str(origin))
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(origin), str(clone))
    return clone


def test_list_files_from_trunk_not_worktree(fixture_repo: Path):
    (fixture_repo / "untracked.txt").write_text("nope")
    t = resolve_trunk(fixture_repo)
    assert list_files(fixture_repo, t.rev) == ["README.md", "bin.dat", "src/a/hot.py", "src/a/old.py", "src/b/b.py"]


def test_blob_locs_text_binary_and_missing_newline(fixture_repo: Path):
    t = resolve_trunk(fixture_repo)
    locs = blob_locs(fixture_repo, t.rev, ["src/a/hot.py", "bin.dat", "src/b/b.py", "README.md"])
    assert locs == {"src/a/hot.py": 5, "bin.dat": None, "src/b/b.py": 1, "README.md": 1}


def test_blob_locs_empty_input(fixture_repo: Path):
    assert blob_locs(fixture_repo, "HEAD", []) == {}


def test_log_since_excludes_old_commits(fixture_repo: Path):
    t = resolve_trunk(fixture_repo)
    since = datetime(2025, 12, 1, tzinfo=timezone.utc)
    cs = log_since(fixture_repo, t.rev, since)
    assert [c.author for c in cs] == ["A", "B", "A"]
    assert cs[0].files == ("src/a/hot.py",)
    assert cs[2].files == ("src/a/hot.py", "src/b/b.py")


def test_scan_git_windows_and_counts(fixture_repo: Path):
    t = resolve_trunk(fixture_repo)
    g = scan_git(fixture_repo, t)
    assert g.windows.as_of == D3
    assert g.windows.since_90d == "2025-12-01T12:00:00Z"
    assert g.windows.since_30d == "2026-01-30T12:00:00Z"
    assert (g.commits_total, g.commits_90d, g.commits_30d, g.authors_90d) == (4, 3, 2, 2)
    assert (g.first_commit, g.last_commit) == (D0, D3)


def test_scan_git_file_stats(fixture_repo: Path):
    g = scan_git(fixture_repo, resolve_trunk(fixture_repo))
    by = {f.path: f for f in g.files}
    hot = by["src/a/hot.py"]
    assert (hot.loc, hot.commits_90d, hot.commits_30d, hot.authors_90d, hot.last_change) == (5, 3, 2, 2, D3)
    old = by["src/a/old.py"]
    assert (old.loc, old.commits_90d, old.commits_30d, old.authors_90d, old.last_change) == (1, 0, 0, 0, None)
    assert by["bin.dat"].loc is None and by["bin.dat"].commits_30d == 1
    assert [f.path for f in g.files] == sorted(f.path for f in g.files)


def test_scan_git_dir_aggregates(fixture_repo: Path):
    g = scan_git(fixture_repo, resolve_trunk(fixture_repo))
    by = {d.path: d for d in g.dirs}
    assert set(by) == {"", "src", "src/a", "src/b"}
    assert (by[""].files, by[""].loc, by[""].commits_90d, by[""].commits_30d) == (5, 8, 3, 2)
    assert (by["src/a"].files, by["src/a"].loc, by["src/a"].commits_90d, by["src/a"].commits_30d) == (2, 6, 3, 2)
    assert (by["src/b"].files, by["src/b"].commits_90d, by["src/b"].commits_30d) == (1, 1, 0)
    assert by["src"].commits_90d == 3   # ein Commit zählt je Verzeichnis nur einmal


def test_scan_git_hotspots_ordered_and_text_only(fixture_repo: Path):
    g = scan_git(fixture_repo, resolve_trunk(fixture_repo))
    assert [(h.path, h.score) for h in g.hotspots] == [("src/a/hot.py", 15), ("src/b/b.py", 1)]
    assert "bin.dat" not in {h.path for h in g.hotspots}


@pytest.mark.parametrize("path,expected", [
    ("src/A/Properties/Resources.Designer.cs", True),
    ("src/Data/Migrations/20260101_Init.cs", True),
    ("src/Data/AppDbContextModelSnapshot.cs", True),
    ("web/dist/app.min.js", True),
    ("package-lock.json", True),
    ("proto/x_pb2.py", True),
    ("src/A/Service.cs", False),
    ("src/Designer/Editor.cs", False),
    ("README.md", False),
])
def test_is_generated_defaults(path, expected):
    assert is_generated(path, GENERATED_DEFAULT) is expected


def test_is_generated_extra_glob_and_no_globs():
    assert is_generated("gen/out.py", ("gen/*",))
    assert not is_generated("gen/out.py", ())


def test_scan_git_generated_flag_excludes_from_hotspots(fixture_repo: Path):
    g = scan_git(fixture_repo, resolve_trunk(fixture_repo), generated=("src/a/hot.py",))
    by = {f.path: f for f in g.files}
    assert by["src/a/hot.py"].generated is True and by["src/b/b.py"].generated is False
    assert by["src/a/hot.py"].commits_90d == 3            # Zählung bleibt
    assert [h.path for h in g.hotspots] == ["src/b/b.py"]  # nur aus Hotspots raus


def test_scan_git_top_limits_hotspots(fixture_repo: Path):
    g = scan_git(fixture_repo, resolve_trunk(fixture_repo), top=1)
    assert [h.path for h in g.hotspots] == ["src/a/hot.py"]


def test_scan_git_as_of_override_moves_windows(fixture_repo: Path):
    as_of = datetime(2026, 2, 1, tzinfo=timezone.utc)   # c2/c3 liegen danach → nicht gezählt
    g = scan_git(fixture_repo, resolve_trunk(fixture_repo), as_of=as_of)
    assert (g.commits_90d, g.commits_30d) == (1, 1)
    assert g.windows.as_of == "2026-02-01T00:00:00Z"


def test_scan_git_ignores_merge_commits_in_windows(fixture_repo: Path, tmp_path: Path):
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(tmp_path / "origin.git"), str(other))
    git(other, "checkout", "-q", "-b", "feat")
    commit(other, "feat", {"src/b/new.py": "n\n"}, date="2026-03-02T12:00:00Z", author="C")
    git(other, "checkout", "-q", "main")
    git(other, "merge", "-q", "--no-ff", "-m", "merge feat", "feat", date="2026-03-03T12:00:00Z")
    git(other, "push", "-q", "origin", "main")
    git(fixture_repo, "fetch", "-q", "origin")
    g = scan_git(fixture_repo, resolve_trunk(fixture_repo))
    assert g.commits_total == 6           # inkl. Merge
    assert g.commits_90d == 4             # ohne Merge
    assert g.windows.as_of == "2026-03-03T12:00:00Z"   # Merge-Commit ist der Trunk-Rev
    assert {f.path for f in g.files} >= {"src/b/new.py"}


def test_scan_git_deleted_file_in_window_not_in_model(fixture_repo: Path, tmp_path: Path):
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(tmp_path / "origin.git"), str(other))
    (other / "src/b/b.py").unlink()
    git(other, "add", "-A")
    git(other, "commit", "-q", "-m", "rm", date="2026-03-04T12:00:00Z")
    git(other, "push", "-q", "origin", "main")
    git(fixture_repo, "fetch", "-q", "origin")
    g = scan_git(fixture_repo, resolve_trunk(fixture_repo))
    assert "src/b/b.py" not in {f.path for f in g.files}
    assert g.commits_90d == 4
