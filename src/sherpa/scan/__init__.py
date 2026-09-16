"""``sherpa scan`` — Codebase deterministisch erfassen. Schicht T0 (Git) in ``t0_git``."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sherpa import __version__, config, gitinfo
from sherpa.model import SCHEMA_VERSION, Model
from sherpa.scan.t0_git import scan_git


def parse_as_of(value: str) -> datetime:
    """``YYYY-MM-DD`` oder volles ISO-8601. Datum ohne Zeit = 00:00 UTC. Ohne Zeitzone = UTC."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def scan(repo: Path, *, trunk: str | None = None, fetch: bool = True,
         as_of: datetime | None = None, hotspots: int | None = None) -> Model:
    """Reihenfolge: Konfig laden → (fetch) → Trunk (ADR-0003) → T0.

    CLI-Argumente schlagen ``sherpa.toml``; ``as_of`` ohne Angabe = Committer-Datum des Trunk-Revs.
    """
    repo = repo.resolve()
    cfg = config.load(repo)
    if fetch:
        gitinfo.fetch_origin(repo)
    t = gitinfo.resolve_trunk(repo, override=trunk or cfg.scan.trunk)
    git_layer = scan_git(repo, t, as_of=as_of, top=hotspots or cfg.scan.hotspots, generated=cfg.scan.generated)
    return Model(
        sherpa=__version__,
        schema_version=SCHEMA_VERSION,
        repo=repo.name,
        origin=gitinfo.origin_url(repo),
        git=git_layer,
    )
