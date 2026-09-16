"""Schicht T0: Churn, Hotspots, Dateibaum — nur aus Git, nur gegen ``origin/<trunk>``.

Entscheidungen (Owner dieses Moduls):
- Dateibaum und LOC kommen aus dem Trunk-Rev (``git ls-tree``/``cat-file``), nicht aus dem Working Tree.
- Zeitfenster enden bei ``as_of`` = Committer-Datum des Trunk-Revs (Default). Gleicher Rev → gleiche Zahlen.
- Fenster zählen Nicht-Merge-Commits (``--no-merges``); ``commits_total`` zählt alle.
- Committer-Datum (``%cI``) überall, weil ``git --since`` ebenfalls danach filtert.
- Hotspot-Score = commits_90d × loc (Tornhill, „Your Code as a Crime Scene": Churn × Komplexitäts-Proxy).
- Generierte Dateien (Globs aus ``config``) tragen ``generated: true`` und sind nie Hotspot.
"""
from __future__ import annotations

import subprocess
from collections import defaultdict
from fnmatch import fnmatchcase
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sherpa.gitinfo import GitError, Trunk
from sherpa.model import DirStat, FileStat, GitLayer, Hotspot, TrunkInfo, Windows

WINDOW_LONG = timedelta(days=90)
WINDOW_SHORT = timedelta(days=30)
DIR_DEPTH = 2
_REC, _UNIT = "\x1e", "\x1f"


@dataclass(frozen=True)
class Commit:
    sha: str
    author: str
    date: datetime          # UTC
    files: tuple[str, ...]


def _run(repo: Path, *args: str, stdin: bytes | None = None) -> bytes:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, input=stdin)
    if r.returncode != 0:
        raise GitError(r.stderr.decode(errors="replace").strip() or f"git {' '.join(args)} failed")
    return r.stdout


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_date(s: str) -> datetime:
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def list_files(repo: Path, ref: str) -> list[str]:
    out = _run(repo, "ls-tree", "-r", "-z", "--name-only", ref).decode("utf-8", errors="surrogateescape")
    return sorted(p for p in out.split("\0") if p)


def blob_locs(repo: Path, ref: str, paths: list[str]) -> dict[str, int | None]:
    """LOC je Datei über EIN ``git cat-file --batch``. Binär (NUL im Inhalt) → None."""
    if not paths:
        return {}
    stdin = "".join(f"{ref}:{p}\n" for p in paths).encode("utf-8", errors="surrogateescape")
    out = _run(repo, "cat-file", "--batch", stdin=stdin)
    locs: dict[str, int | None] = {}
    pos = 0
    for p in paths:
        nl = out.index(b"\n", pos)
        header = out[pos:nl].decode()
        pos = nl + 1
        parts = header.split()
        if len(parts) < 3 or parts[1] != "blob":     # "missing" oder anderer Typ (Submodule = commit)
            locs[p] = None
            continue
        size = int(parts[2])
        content = out[pos:pos + size]
        pos += size + 1                                 # Inhalt + abschliessendes "\n"
        if b"\0" in content:
            locs[p] = None
        else:
            locs[p] = content.count(b"\n") + (1 if content and not content.endswith(b"\n") else 0)
    return locs


def commit_date(repo: Path, ref: str) -> datetime:
    return _parse_date(_run(repo, "log", "-1", "--format=%cI", ref).decode().strip())


def root_commit_date(repo: Path, ref: str) -> datetime:
    roots = _run(repo, "rev-list", "--max-parents=0", ref).decode().split()
    return min(commit_date(repo, r) for r in roots)


def count_commits(repo: Path, ref: str) -> int:
    return int(_run(repo, "rev-list", "--count", ref).decode().strip())


def log_since(repo: Path, ref: str, since: datetime) -> list[Commit]:
    """Nicht-Merge-Commits seit ``since`` mit berührten Dateien. Ein Prozess, feste Trennzeichen."""
    out = _run(
        repo, "log", ref, "--no-merges", f"--since={_iso(since)}",
        f"--format={_REC}%H{_UNIT}%an{_UNIT}%cI", "--name-only",
    ).decode("utf-8", errors="surrogateescape")
    commits: list[Commit] = []
    for rec in out.split(_REC):
        if not rec.strip():
            continue
        head, _, body = rec.partition("\n")
        sha, author, date = head.split(_UNIT)
        files = tuple(sorted({ln for ln in body.splitlines() if ln}))
        commits.append(Commit(sha, author, _parse_date(date), files))
    return commits


def _dir_prefixes(path: str) -> list[str]:
    parts = path.split("/")[:-1]
    return [""] + ["/".join(parts[:i]) for i in range(1, min(len(parts), DIR_DEPTH) + 1)]


def is_generated(path: str, globs: tuple[str, ...]) -> bool:
    name = path.rsplit("/", 1)[-1]
    return any(fnmatchcase(path, g) or fnmatchcase(name, g) for g in globs)


def scan_git(repo: Path, trunk: Trunk, *, as_of: datetime | None = None, top: int = 20,
             generated: tuple[str, ...] = ()) -> GitLayer:
    as_of = as_of or commit_date(repo, trunk.rev)
    since_90, since_30 = as_of - WINDOW_LONG, as_of - WINDOW_SHORT

    commits = [c for c in log_since(repo, trunk.rev, since_90) if since_90 < c.date <= as_of]
    paths = list_files(repo, trunk.rev)
    locs = blob_locs(repo, trunk.rev, paths)
    present = set(paths)

    c90: dict[str, int] = defaultdict(int)
    c30: dict[str, int] = defaultdict(int)
    authors: dict[str, set[str]] = defaultdict(set)
    last: dict[str, datetime] = {}
    d90: dict[str, set[str]] = defaultdict(set)
    d30: dict[str, set[str]] = defaultdict(set)
    in30 = 0
    for c in commits:
        short = c.date > since_30
        in30 += short
        for f in c.files:
            if f not in present:              # im Fenster gelöscht/umbenannt → nicht im Baum
                continue
            c90[f] += 1
            authors[f].add(c.author)
            if f not in last or c.date > last[f]:
                last[f] = c.date
            if short:
                c30[f] += 1
            for d in _dir_prefixes(f):
                d90[d].add(c.sha)
                if short:
                    d30[d].add(c.sha)

    files = [FileStat(p, locs[p], is_generated(p, generated), c90[p], c30[p], len(authors[p]),
                      _iso(last[p]) if p in last else None) for p in paths]

    dfiles: dict[str, int] = defaultdict(int)
    dloc: dict[str, int] = defaultdict(int)
    for p in paths:
        for d in _dir_prefixes(p):
            dfiles[d] += 1
            dloc[d] += locs[p] or 0
    dirs = [DirStat(d, dfiles[d], dloc[d], len(d90[d]), len(d30[d])) for d in sorted(dfiles)]

    hot = [Hotspot(f.path, f.commits_90d, f.loc, f.commits_90d * f.loc)
           for f in files if f.commits_90d >= 1 and f.loc is not None and not f.generated]
    hot.sort(key=lambda h: (-h.score, h.path))

    return GitLayer(
        trunk=TrunkInfo(trunk.ref, trunk.source, trunk.rev),
        windows=Windows(_iso(as_of), _iso(since_90), _iso(since_30)),
        commits_total=count_commits(repo, trunk.rev),
        commits_90d=len(commits),
        commits_30d=in30,
        authors_90d=len({c.author for c in commits}),
        first_commit=_iso(root_commit_date(repo, trunk.rev)),
        last_commit=_iso(commit_date(repo, trunk.rev)),
        files=files,
        dirs=dirs,
        hotspots=hot[:top],
    )
