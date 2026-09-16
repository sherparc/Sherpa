"""``sherpa scan`` — Codebase deterministisch erfassen. Schicht T0 (Git) in ``t0_git``."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sherpa import __version__, config, gitinfo
from sherpa.model import SCHEMA_VERSION, Conventions, Model
from sherpa.scan.t0_git import build_git_layer, collect
from sherpa.scan.t1_modules import build_modules, detect_conventions, load_manifests


def parse_as_of(value: str) -> datetime:
    """``YYYY-MM-DD`` oder volles ISO-8601. Datum ohne Zeit = 00:00 UTC. Ohne Zeitzone = UTC."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def scan(repo: Path, *, trunk: str | None = None, fetch: bool = True,
         as_of: datetime | None = None, hotspots: int | None = None) -> Model:
    """Reihenfolge: Konfig laden → (fetch) → Trunk (ADR-0003) → T0 (Git) → T1 (Module, Konventionen).

    CLI-Argumente schlagen ``sherpa.toml``; ``as_of`` ohne Angabe = Committer-Datum des Trunk-Revs.
    """
    repo = repo.resolve()
    cfg = config.load(repo)
    if fetch:
        gitinfo.fetch_origin(repo)
    t = gitinfo.resolve_trunk(repo, override=trunk or cfg.scan.trunk)
    data = collect(repo, t, as_of=as_of)
    git_layer = build_git_layer(repo, data, top=hotspots or cfg.scan.hotspots, generated=cfg.scan.generated)
    paths = list(data.paths)
    modules = build_modules(data, git_layer.files, load_manifests(repo, t.rev, paths))
    languages, ci, containers = detect_conventions(paths, data.locs)
    return Model(
        sherpa=__version__,
        schema_version=SCHEMA_VERSION,
        repo=repo.name,
        origin=gitinfo.origin_url(repo),
        git=git_layer,
        modules=modules,
        conventions=Conventions(languages, ci, containers),
    )
