"""sherpa.toml im Repo — optionale Konfiguration (stdlib ``tomllib``, darum TOML statt YAML).

::

    [scan]
    trunk = "dev"      # Override für ADR-0003; mit oder ohne "origin/"
    hotspots = 20      # Anzahl Hotspots im Modell
    generated = ["*.g.cs", "gen/**"]   # zusätzliche Globs für generierte Dateien (ergänzt GENERATED_DEFAULT)
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_NAME = "sherpa.toml"

# Generierte Dateien: bleiben im Modell (files/dirs), zählen aber nicht als Hotspot — Churn dort ist
# Werkzeug-Rauschen, keine Entwickler-Arbeit (Tornhill: Hotspots nur auf Hand-Code). fnmatch-Globs
# gegen den vollen Repo-Pfad; "**" wird von fnmatch wie "*" behandelt (matcht auch über "/").
GENERATED_DEFAULT: tuple[str, ...] = (
    "*.Designer.cs", "*.g.cs", "*.g.i.cs", "*ModelSnapshot.cs", "*.resx",      # .NET, EF-Migrations
    "*/Migrations/*.cs", "*.generated.*", "*.gen.*", "*_pb2.py", "*.pb.go",    # Migrationen, Codegen, protobuf
    "*.min.js", "*.min.css", "*.bundle.js", "*.map",                             # Frontend-Bundles
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock",
    "Cargo.lock", "go.sum", "Gemfile.lock", "composer.lock", "packages.lock.json",
    "*.snap", "*.svg", "*.csv", "*.sql.gz",
)


@dataclass(frozen=True)
class ScanConfig:
    trunk: str | None = None
    hotspots: int = 20
    generated: tuple[str, ...] = GENERATED_DEFAULT


@dataclass(frozen=True)
class Config:
    scan: ScanConfig = ScanConfig()


def load(repo: Path) -> Config:
    p = repo / CONFIG_NAME
    if not p.exists():
        return Config()
    raw = tomllib.loads(p.read_text(encoding="utf-8"))
    s = raw.get("scan", {})
    extra = tuple(str(g) for g in s.get("generated", ()))
    return Config(scan=ScanConfig(trunk=s.get("trunk"), hotspots=int(s.get("hotspots", 20)),
                                  generated=GENERATED_DEFAULT + extra))
