"""Datenmodell von ``codebase-model.json`` (Schicht T0). Feldsemantik: ``schemas/codebase-model.schema.json``.

Serialisierung ist deterministisch: sortierte Schlüssel, feste Einrückung, ``\\n`` am Ende.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

SCHEMA_VERSION = 2
SCHEMA_PATH = Path(__file__).parent / "schemas" / "codebase-model.schema.json"


@dataclass(frozen=True)
class TrunkInfo:
    ref: str
    source: str
    rev: str


@dataclass(frozen=True)
class Windows:
    as_of: str  # ISO-8601 UTC; Ende beider Fenster
    since_90d: str
    since_30d: str


@dataclass(frozen=True)
class FileStat:
    path: str
    loc: int | None  # None = binär
    generated: bool  # matcht ein Generated-Glob (config.GENERATED_DEFAULT + sherpa.toml); kein Hotspot
    commits_90d: int
    commits_30d: int
    authors_90d: int
    last_change: str | None  # ISO-8601 UTC des letzten Commits im 90d-Fenster, sonst None


@dataclass(frozen=True)
class DirStat:
    path: str  # "src/Foo" — Tiefe 1 und 2, ohne Slash am Ende; "" = Wurzel
    files: int
    loc: int
    commits_90d: int
    commits_30d: int


@dataclass(frozen=True)
class Hotspot:
    path: str
    commits_90d: int
    loc: int
    score: int  # commits_90d * loc (Tornhill: Churn × Grösse als Komplexitäts-Proxy)


@dataclass(frozen=True)
class ModuleStat:
    id: str
    path: str  # Verzeichnis des Manifests, "" = Wurzel
    kind: str  # dotnet | python | node | go | rust | java
    manifest: str
    is_test: bool  # eigenes Test-Modul (dotnet)
    files: int
    loc: int
    test_files: int  # Testdateien innerhalb des Moduls
    deps: list[str]  # Modul-ids im Repo
    dependents: list[str]
    tested_by: list[str]  # Test-Module, die dieses Modul referenzieren
    commits_90d: int
    commits_30d: int
    authors_90d: int
    hotspots: list[str]  # Top-Pfade nach commits×loc innerhalb des Moduls


@dataclass(frozen=True)
class Conventions:
    languages: dict[str, int]  # Sprache → LOC, absteigend
    ci: list[str]
    containers: list[str]


@dataclass(frozen=True)
class GitLayer:
    trunk: TrunkInfo
    windows: Windows
    commits_total: int
    commits_90d: int
    commits_30d: int
    authors_90d: int
    first_commit: str
    last_commit: str
    files: list[FileStat] = field(default_factory=list)
    dirs: list[DirStat] = field(default_factory=list)
    hotspots: list[Hotspot] = field(default_factory=list)


@dataclass(frozen=True)
class Model:
    sherpa: str
    schema_version: int
    repo: str  # Basename des Repo-Verzeichnisses
    origin: str  # URL von origin
    git: GitLayer
    modules: list[ModuleStat] = field(default_factory=list)
    conventions: Conventions = field(default_factory=lambda: Conventions({}, [], []))

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, indent=2, ensure_ascii=False) + "\n"

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")


def validate(data: dict) -> None:
    """Gegen das JSON-Schema prüfen. Braucht ``jsonschema`` (dev-Extra); ohne Paket: no-op."""
    try:
        import jsonschema  # type: ignore
    except ImportError:  # pragma: no cover
        return
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(data, schema)
