"""Git-Fakten eines Repos — deterministisch, ohne Netz (ausser fetch_origin).

Grundsatz (Trunk-Disziplin, ADR-0003): gemessen wird immer gegen ``origin/<trunk>``,
nie gegen den lokalen ``HEAD`` — der steht oft auf einem Task-Branch.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

REMOTE = "origin"
# Reihenfolge = Priorität, wenn origin/HEAD nicht gesetzt ist.
TRUNK_CANDIDATES = ("main", "master", "dev", "develop", "trunk")


class GitError(RuntimeError):
    """Kein Git-Repo, kein origin oder kein erkennbarer Trunk."""


@dataclass(frozen=True)
class Trunk:
    ref: str  # z. B. "origin/main"
    source: str  # "override" | "origin/HEAD" | "candidate"
    rev: str  # voller SHA


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
    """Einziger Netzzugriff. Wird von ``scan`` vor resolve_trunk aufgerufen (``--no-fetch`` überspringt)."""
    _git(repo, "fetch", "--quiet", REMOTE)


def resolve_trunk(repo: Path, override: str | None = None) -> Trunk:
    """Trunk bestimmen, immer als ``origin/<branch>``.

    Reihenfolge:
      1. ``override`` aus sherpa.yaml (``trunk: dev`` oder ``trunk: origin/dev``)
      2. ``refs/remotes/origin/HEAD`` (wird von ``git clone`` gesetzt, sonst ``git remote set-head origin -a``)
      3. erster existierender Kandidat aus TRUNK_CANDIDATES
    """
    if not is_repo(repo):
        raise GitError(f"{repo} ist kein Git-Repo")
    if not has_remote(repo):
        raise GitError(f"{repo} hat kein Remote '{REMOTE}' — Sherpa scannt nur gegen origin")

    if override:
        ref = override if override.startswith(f"{REMOTE}/") else f"{REMOTE}/{override}"
        if not ref_exists(repo, ref):
            raise GitError(f"Trunk-Override '{override}' existiert nicht als {ref}")
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
        f"kein Trunk gefunden: origin/HEAD nicht gesetzt und keiner von {TRUNK_CANDIDATES} auf {REMOTE}. "
        f"Abhilfe: 'git remote set-head {REMOTE} -a' oder 'trunk:' in sherpa.yaml"
    )
