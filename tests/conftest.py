"""Fixture repos are built programmatically — no binary fixtures, every run identical."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
    "HOME": "/nonexistent",  # do not read the user gitconfig
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
}


def git(repo: Path, *args: str, date: str | None = None, author: str | None = None) -> str:
    env = {**os.environ, **ENV}  # extend, do not replace: Windows needs PATH/SYSTEMROOT for git
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    if author:
        env["GIT_AUTHOR_NAME"] = author
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=env, check=True)
    return r.stdout.strip()


def commit(
    repo: Path,
    msg: str,
    files: dict[str, str | bytes] | None = None,
    *,
    date: str | None = None,
    author: str | None = None,
) -> str:
    """Commit with a fixed date/author — fixture SHAs are identical across runs."""
    for name, content in (files or {"f.txt": msg}).items():
        p = repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg, date=date, author=author)
    return git(repo, "rev-parse", "HEAD")


def copy_repo(built: Path, into: Path) -> Path:
    """A per-test copy of a session-built fixture directory (seed, ``origin.git``, the clone): one ``copytree``
    instead of dozens of git subprocesses — the difference between 45 s and 6 min on the Windows runner. The
    clone's ``origin`` is re-pointed at the copied bare repository so pushes and fetches stay inside the test."""
    dst = into / built.name
    shutil.copytree(built, dst, symlinks=True)
    for clone in (
        d for d in dst.iterdir() if d.is_dir() and d.name not in ("seed", "origin.git") and (d / ".git").exists()
    ):
        git(clone, "remote", "set-url", "origin", str(dst / "origin.git"))
    return dst


def _session_repo(name: str, module: str, builder: str):
    """Two fixtures from one builder function: ``<name>_built`` (session scope, built once) and ``<name>``
    (a fresh copy per test). The builder lives in the test module that documents the fixture; it is imported
    lazily so conftest stays importable first."""

    @pytest.fixture(scope="session", name=f"{name}_built")
    def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
        import importlib

        build = getattr(importlib.import_module(module), builder)
        return build(tmp_path_factory.mktemp(name, numbered=False))

    @pytest.fixture(name=name)
    def per_test(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
        src: Path = request.getfixturevalue(f"{name}_built")
        return copy_repo(src.parent, tmp_path) / src.name

    return built, per_test


active_repo_built, active_repo = _session_repo("active_repo", "tests.test_plan", "build_active_repo")
poly_repo_built, poly_repo = _session_repo("poly_repo", "tests.test_t1_modules", "build_poly_repo")


@pytest.fixture
def make_origin(tmp_path: Path):
    """Create a bare origin with branches; returns (origin_path, {branch: sha})."""

    def _make(branches: tuple[str, ...] = ("main",)) -> tuple[Path, dict[str, str]]:
        work = tmp_path / "seed"
        work.mkdir()
        git(work, "init", "-q", "-b", branches[0])
        shas = {branches[0]: commit(work, "init")}
        for b in branches[1:]:
            git(work, "checkout", "-q", "-b", b)
            shas[b] = commit(work, f"on {b}")
        git(work, "checkout", "-q", branches[0])  # HEAD of the seed = first branch -> origin/HEAD
        origin = tmp_path / "origin.git"
        git(tmp_path, "clone", "-q", "--bare", str(work), str(origin))
        return origin, shas

    return _make


@pytest.fixture
def make_clone(tmp_path: Path):
    """Clone of origin; ``set_head=False`` removes origin/HEAD (case: a manually added remote)."""

    def _make(origin: Path, set_head: bool = True) -> Path:
        dst = tmp_path / "clone"
        git(tmp_path, "clone", "-q", str(origin), str(dst))
        if not set_head:
            git(dst, "remote", "set-head", "origin", "-d")
        return dst

    return _make


@pytest.fixture(autouse=True)
def no_network_update_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """No test — in-process or via subprocess — ever calls the GitHub Releases API, and the cache stays in tmp."""
    monkeypatch.setenv("SHERPA_NO_UPDATE_CHECK", "1")
    monkeypatch.setenv("SHERPA_CACHE_DIR", str(tmp_path / "cache"))
