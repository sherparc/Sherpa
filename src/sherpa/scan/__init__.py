"""``sherpa scan`` — capture the codebase deterministically: T0 git (``t0_git``), T1 modules (``t1_modules``),
generator families (``generators``)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sherpa import __version__, config, gitinfo
from sherpa.model import SCHEMA_VERSION, Conventions, Model
from sherpa.scan.generators import Matcher, detect_generators
from sherpa.scan.t0_git import build_git_layer, collect
from sherpa.scan.t1_modules import (
    assign_files,
    build_modules_from,
    compute_coupling,
    detect_conventions,
    find_modules,
    load_manifests,
)


def parse_as_of(value: str) -> datetime:
    """``YYYY-MM-DD`` or full ISO-8601. A date without time = 00:00 UTC. Without a time zone = UTC."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def scan(
    repo: Path,
    *,
    trunk: str | None = None,
    fetch: bool = True,
    as_of: datetime | None = None,
    hotspots: int | None = None,
) -> Model:
    """Load config → (fetch) → trunk (ADR-0003) → detect modules → generators → T0 (git) → T1 (module stats).

    CLI arguments beat ``sherpa.toml``; ``as_of`` defaults to the committer date of the trunk rev.
    """
    repo = repo.resolve()
    cfg = config.load(repo)
    if fetch:
        gitinfo.fetch_origin(repo)
    t = gitinfo.resolve_trunk(repo, override=trunk or cfg.scan.trunk)
    data = collect(repo, t, as_of=as_of)
    paths = list(data.paths)
    raw = find_modules(paths, load_manifests(repo, t.rev, paths))
    owner = assign_files(paths, raw)
    generators, outputs = detect_generators(paths, data.locs, owner, Matcher(cfg.scan.custom_generated))
    git_layer = build_git_layer(
        repo, data, top=hotspots or cfg.scan.hotspots, generated=cfg.scan.generated, outputs=outputs
    )
    coupling, coupling_stats = compute_coupling(data, owner, [m.id for m in raw])
    modules = build_modules_from(data, git_layer.files, raw, owner, outputs=outputs, coupling=coupling)
    languages, ci, containers = detect_conventions(paths, data.locs)
    return Model(
        sherpa=__version__,
        schema_version=SCHEMA_VERSION,
        repo=repo.name,
        origin=gitinfo.origin_url(repo),
        git=git_layer,
        modules=modules,
        generators=generators,
        conventions=Conventions(languages, ci, containers),
        coupling=coupling_stats,
    )
