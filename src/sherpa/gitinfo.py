"""Git facts of a repository — deterministic, offline (except fetch_origin).

Principle (trunk discipline, ADR-0003): everything is measured against ``origin/<trunk>``,
never against the local ``HEAD`` — that one is usually on a task branch.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

REMOTE = "origin"
# Order = priority when origin/HEAD is not set.
TRUNK_CANDIDATES = ("main", "master", "dev", "develop", "trunk")


class GitError(RuntimeError):
    """No git repo, no origin, or no recognisable trunk."""


@dataclass(frozen=True)
class Trunk:
    ref: str  # e.g. "origin/main"
    source: str  # "override" | "origin/HEAD" | "candidate"
    rev: str  # full SHA


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise GitError(r.stderr.strip() or f"git {' '.join(args)} failed")
    return r.stdout.strip()


def is_repo(repo: Path) -> bool:
    try:
        return _git(repo, "rev-parse", "--is-inside-work-tree") == "true"
    except GitError:
        return False


def ignored(repo: Path, paths: list[str]) -> set[str]:
    """The subset of ``paths`` (repo-relative) that git ignores; empty outside a repository."""
    if not paths or not is_repo(repo):
        return set()
    r = subprocess.run(
        ["git", "-C", str(repo), "check-ignore", "--stdin", "-z"],
        input="\0".join(paths) + "\0",
        capture_output=True,
        text=True,
    )
    return {x for x in r.stdout.split("\0") if x} if r.returncode in (0, 1) else set()


def nested_repositories(repo: Path) -> list[str]:
    """Directories below the root that are repositories of their own — a ``.git`` directory or worktree file
    inside: submodules, clones kept in the tree, a harness checked out under ``.claude/``. Sherpa works with one
    repository (ADR-0045), so ``apply`` and ``adopt`` refuse when this is not empty. Dependency and build
    directories are not walked; of the dot-directories only the harness homes are."""
    from sherpa.check import SKIP_DIRS

    found: list[str] = []
    stack = [repo]
    while stack:
        d = stack.pop()
        try:
            entries = sorted(d.iterdir())
        except OSError:
            continue
        for p in entries:
            if p.name == ".git" and d != repo:
                found.append(d.relative_to(repo).as_posix())
            elif p.is_dir() and p.name not in SKIP_DIRS:
                if p.name.startswith(".") and p.name not in (".claude", ".agents"):
                    continue
                stack.append(p)
    return sorted(found)


def has_remote(repo: Path, name: str = REMOTE) -> bool:
    try:
        return name in _git(repo, "remote").splitlines()
    except GitError:
        return False


def ref_exists(repo: Path, ref: str) -> bool:
    try:
        _git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        return True
    except GitError:
        return False


def rev(repo: Path, ref: str) -> str:
    return _git(repo, "rev-parse", f"{ref}^{{commit}}")


def origin_url(repo: Path) -> str:
    return _git(repo, "remote", "get-url", REMOTE)


def fetch_origin(repo: Path) -> None:
    """The only network access. Called by ``scan`` before resolve_trunk (``--no-fetch`` skips it)."""
    _git(repo, "fetch", "--quiet", REMOTE)


def resolve_trunk(repo: Path, override: str | None = None) -> Trunk:
    """Determine the trunk, always as ``origin/<branch>``.

    Order:
      1. ``override`` from sherpa.toml (``trunk = "dev"`` or ``trunk = "origin/dev"``)
      2. ``refs/remotes/origin/HEAD`` (set by ``git clone``, otherwise ``git remote set-head origin -a``)
      3. first existing candidate from TRUNK_CANDIDATES
    """
    if not is_repo(repo):
        raise GitError(f"{repo} is not a git repository")
    if not has_remote(repo):
        raise GitError(f"{repo} has no remote '{REMOTE}' — sherpa only scans against origin")

    if override:
        ref = override if override.startswith(f"{REMOTE}/") else f"{REMOTE}/{override}"
        if not ref_exists(repo, ref):
            raise GitError(f"trunk override '{override}' does not exist as {ref}")
        return Trunk(ref, "override", rev(repo, ref))

    try:
        target = _git(repo, "symbolic-ref", "--quiet", f"refs/remotes/{REMOTE}/HEAD")
        ref = target.removeprefix("refs/remotes/")
        if ref_exists(repo, ref):
            return Trunk(ref, "origin/HEAD", rev(repo, ref))
    except GitError:
        pass

    for name in TRUNK_CANDIDATES:
        ref = f"{REMOTE}/{name}"
        if ref_exists(repo, ref):
            return Trunk(ref, "candidate", rev(repo, ref))

    raise GitError(
        f"no trunk found: origin/HEAD is not set and none of {TRUNK_CANDIDATES} exists on {REMOTE}. "
        f"Fix: 'git remote set-head {REMOTE} -a' or 'trunk' in sherpa.toml"
    )
