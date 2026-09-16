"""sherpa.toml in the repo — optional configuration (stdlib ``tomllib``, hence TOML rather than YAML).

::

    [scan]
    trunk = "dev"      # override for ADR-0003; with or without "origin/"
    hotspots = 20      # number of hotspots in the model
    generated = ["*.g.cs", "gen/**"]   # extra globs for generated files (family "custom")

    [plan]                             # thresholds: rank AND floor (ADR-0006); defaults in PlanConfig
    agent_top = 0.25                   # agent: top quartile by commits_90d …
    agent_min_commits_90d = 20         # … and floors on commits, files, authors
    agent_min_files = 30
    agent_min_authors_90d = 2
    librarian_top_n = 2                # librarian: top N by commits_30d …
    librarian_min_commits_30d = 30     # … and floor (30 d) or …
    librarian_min_commits_90d = 80     # … floor (90 d)
    dir_min_files = 10                 # a directory without a module counts as a unit from this many files
    generated_share = 0.5              # from this share of generator output: no agent/librarian, a skill instead
    skill_min_generated_files = 5      # skill proposal from this many generated files (or config, see rules)
    owner_doc_min_files = 5            # owner doc from this many files, unless something depends on the unit
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

from sherpa.scan.generators import GENERATED_GLOBS, NOISE

CONFIG_NAME = "sherpa.toml"

# Never a hotspot: generator outputs of all families (scan.generators.FAMILIES, lockfiles included) plus noise
# (images, data, resources). Churn there is tool noise, not developer work (Tornhill: hotspots on hand-written code
# only). Globs without "/" apply to the file name, with "/" to the path; "*" also matches "/".
GENERATED_DEFAULT: tuple[str, ...] = GENERATED_GLOBS + NOISE


@dataclass(frozen=True)
class ScanConfig:
    trunk: str | None = None
    hotspots: int = 20
    generated: tuple[str, ...] = GENERATED_DEFAULT  # hotspot exclusion: defaults + custom
    custom_generated: tuple[str, ...] = ()  # user globs only: generator family "custom"


@dataclass(frozen=True)
class PlanConfig:
    agent_top: float = 0.25
    agent_min_commits_90d: int = 20
    agent_min_files: int = 30
    agent_min_authors_90d: int = 2
    librarian_top_n: int = 2
    librarian_min_commits_30d: int = 30
    librarian_min_commits_90d: int = 80
    dir_min_files: int = 10
    generated_share: float = 0.5
    skill_min_generated_files: int = 5
    owner_doc_min_files: int = 5


@dataclass(frozen=True)
class Config:
    scan: ScanConfig = ScanConfig()
    plan: PlanConfig = PlanConfig()


def load(repo: Path) -> Config:
    p = repo / CONFIG_NAME
    if not p.exists():
        return Config()
    raw = tomllib.loads(p.read_text(encoding="utf-8"))
    s = raw.get("scan", {})
    extra = tuple(str(g) for g in s.get("generated", ()))
    pl = raw.get("plan", {})
    known = {f.name: f.type for f in fields(PlanConfig)}
    unknown = sorted(set(pl) - set(known))
    if unknown:
        raise ValueError(f"sherpa.toml [plan]: unknown keys {unknown}; allowed: {sorted(known)}")
    plan = PlanConfig(**{k: (float(v) if known[k] == "float" else int(v)) for k, v in pl.items()})
    return Config(
        scan=ScanConfig(
            trunk=s.get("trunk"),
            hotspots=int(s.get("hotspots", 20)),
            generated=GENERATED_DEFAULT + extra,
            custom_generated=extra,
        ),
        plan=plan,
    )
