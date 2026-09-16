from pathlib import Path

import pytest

from sherpa import gitinfo
from sherpa.gitinfo import GitError, Trunk, resolve_trunk
from tests.conftest import git, commit


def test_not_a_repo(tmp_path: Path):
    with pytest.raises(GitError, match="kein Git-Repo"):
        resolve_trunk(tmp_path)


def test_repo_without_origin(tmp_path: Path):
    git(tmp_path, "init", "-q", "-b", "main")
    commit(tmp_path, "x")
    with pytest.raises(GitError, match="kein Remote 'origin'"):
        resolve_trunk(tmp_path)


def test_origin_head_wins(make_origin, make_clone):
    origin, shas = make_origin(("dev", "main"))  # origin/HEAD zeigt auf dev (erster Branch)
    clone = make_clone(origin)
    t = resolve_trunk(clone)
    assert t == Trunk("origin/dev", "origin/HEAD", shas["dev"])


def test_candidate_order_when_no_origin_head(make_origin, make_clone):
    origin, shas = make_origin(("dev", "master"))
    clone = make_clone(origin, set_head=False)
    t = resolve_trunk(clone)
    assert t.ref == "origin/master"          # master vor dev laut TRUNK_CANDIDATES
    assert t.source == "candidate"
    assert t.rev == shas["master"]


def test_candidate_dev_only(make_origin, make_clone):
    origin, shas = make_origin(("dev",))
    clone = make_clone(origin, set_head=False)
    assert resolve_trunk(clone) == Trunk("origin/dev", "candidate", shas["dev"])


def test_no_trunk_found(make_origin, make_clone):
    origin, _ = make_origin(("feature-x",))
    clone = make_clone(origin, set_head=False)
    with pytest.raises(GitError, match="kein Trunk gefunden"):
        resolve_trunk(clone)


@pytest.mark.parametrize("override", ["dev", "origin/dev"])
def test_override_with_and_without_prefix(make_origin, make_clone, override):
    origin, shas = make_origin(("main", "dev"))
    clone = make_clone(origin)
    t = resolve_trunk(clone, override=override)
    assert t == Trunk("origin/dev", "override", shas["dev"])


def test_override_missing_branch(make_origin, make_clone):
    origin, _ = make_origin(("main",))
    clone = make_clone(origin)
    with pytest.raises(GitError, match="existiert nicht"):
        resolve_trunk(clone, override="release")


def test_local_head_is_ignored(make_origin, make_clone):
    """Trunk-Disziplin: lokaler Task-Branch mit neuem Commit ändert das Ergebnis nicht."""
    origin, shas = make_origin(("main",))
    clone = make_clone(origin)
    git(clone, "checkout", "-q", "-b", "task/123")
    commit(clone, "local work")
    t = resolve_trunk(clone)
    assert t.rev == shas["main"]
    assert t.rev != git(clone, "rev-parse", "HEAD")


def test_trunk_follows_origin_after_fetch(make_origin, make_clone, tmp_path: Path):
    origin, _ = make_origin(("main",))
    clone = make_clone(origin)
    # zweiter Klon pusht auf origin/main
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(origin), str(other))
    new = commit(other, "upstream change")
    git(other, "push", "-q", "origin", "main")
    assert resolve_trunk(clone).rev != new
    gitinfo.fetch_origin(clone)
    assert resolve_trunk(clone).rev == new


def test_is_repo_and_has_remote(make_origin, make_clone, tmp_path: Path):
    origin, _ = make_origin()
    clone = make_clone(origin)
    assert gitinfo.is_repo(clone) and gitinfo.has_remote(clone)
    assert not gitinfo.is_repo(tmp_path / "nope")
