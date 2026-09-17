"""Data model of ``codebase-model.json``. Field semantics: ``schemas/codebase-model.schema.json``.

Serialisation is deterministic: sorted keys, fixed indentation, trailing ``\\n``.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

SCHEMA_VERSION = 5  # v5: coupling carries its denominator (ADR-0039); v4: sub_dirs and coupling per module
SCHEMA_PATH = Path(__file__).parent / "schemas" / "codebase-model.schema.json"


@dataclass(frozen=True)
class TrunkInfo:
    ref: str
    source: str
    rev: str


@dataclass(frozen=True)
class Windows:
    as_of: str  # ISO-8601 UTC; end of both windows
    since_90d: str
    since_30d: str


@dataclass(frozen=True)
class FileStat:
    path: str
    loc: int | None  # None = binary
    generated: bool  # matches a generated glob (config.GENERATED_DEFAULT + sherpa.toml); never a hotspot
    commits_90d: int
    commits_30d: int
    authors_90d: int
    last_change: str | None  # ISO-8601 UTC of the latest commit in the 90d window, else None


@dataclass(frozen=True)
class DirStat:
    path: str  # "src/Foo" — depth 1 and 2, no trailing slash; "" = root
    files: int
    loc: int
    generated_files: int  # generator outputs below it (scan.generators), not lockfiles/noise
    commits_90d: int
    commits_30d: int
    authors_90d: int


@dataclass(frozen=True)
class Hotspot:
    path: str
    commits_90d: int
    loc: int
    score: int  # commits_90d * loc (Tornhill: churn × size as a complexity proxy)


@dataclass(frozen=True)
class SubDir:
    """A directory inside a module, depths 1–4 below the module's path: the raw material for sub-units of a
    single-manifest repository (ADR-0020). ``source_files`` counts files in the module's own language(s);
    ``package`` is a Python package (``__init__.py``)."""

    path: str  # repo-relative, no trailing slash
    depth: int  # 1 = directly below the module path
    files: int
    source_files: int
    package: bool
    loc: int
    commits_90d: int
    commits_30d: int
    authors_90d: int


@dataclass(frozen=True)
class Coupling:
    """Temporal coupling (Tornhill): ``module`` changed in ``shared`` of this module's commits (``share`` of them).
    Commits above the size cap are excluded — see ``Model.coupling``."""

    module: str
    shared: int
    share: float  # 0.0–1.0 = shared / of
    of: int  # this module's measured commits — below the cap, root excluded — the denominator of share (ADR-0039)


@dataclass(frozen=True)
class CouplingStats:
    cap: int  # commits touching more modules than this are ignored for coupling (squash merges, mass renames)
    skipped_commits: int
    measured_commits: int
    min_shared: int  # floor: partners with fewer shared commits are not listed
    min_share: float
    excluded: str | None = None  # the root module left out as a catch-all when other modules exist (ADR-0026)


@dataclass(frozen=True)
class ModuleStat:
    id: str
    path: str  # directory of the manifest, "" = root
    kind: str  # dotnet | python | node | go | rust | java
    manifest: str
    is_test: bool  # a test module (dotnet project property/package/name, or a test directory in the path)
    files: int
    loc: int
    test_files: int  # test files inside the module
    generated_files: (
        int  # generator outputs in the module (scan.generators); a high share = the knowledge lives in the generator
    )
    deps: list[str]  # module ids within the repo
    dependents: list[str]
    tested_by: list[str]  # test modules referencing this module
    commits_90d: int
    commits_30d: int
    authors_90d: int
    hotspots: list[str]  # top paths by commits×loc within the module
    sub_dirs: list[SubDir] = field(default_factory=list)
    coupling: list[Coupling] = field(default_factory=list)  # top partners, descending by shared commits


@dataclass(frozen=True)
class GeneratorStat:
    """A generator in the repo: family × owning module. Source of skill proposals (ADR-0011)."""

    family: str  # id from scan.generators.FAMILIES or "custom"
    title: str
    module: str | None  # module id owning the generated files; None = no module
    home: str  # common directory of the outputs (else of the config); "" = root
    generated_files: int
    generated_loc: int
    sources: list[str]  # up to MAX_LISTED source paths, closest to home first
    configs: list[str]
    command: str  # regeneration command or hint
    skill: bool  # False = tool-managed (lockfiles), no skill proposal


@dataclass(frozen=True)
class Conventions:
    languages: dict[str, int]  # language → LOC, descending
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
    repo: str  # basename of the repo directory
    origin: str  # URL of origin
    git: GitLayer
    modules: list[ModuleStat] = field(default_factory=list)
    generators: list[GeneratorStat] = field(default_factory=list)
    conventions: Conventions = field(default_factory=lambda: Conventions({}, [], []))
    coupling: CouplingStats = field(default_factory=lambda: CouplingStats(0, 0, 0, 0, 0.0))

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, indent=2, ensure_ascii=False) + "\n"

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def from_dict(cls, d: dict) -> Model:
        """Inverse of ``asdict`` — for ``sherpa plan``, which reads a stored model."""
        if d.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"model has schema_version {d.get('schema_version')}, expected {SCHEMA_VERSION}")
        g = d["git"]
        git = GitLayer(
            trunk=TrunkInfo(**g["trunk"]),
            windows=Windows(**g["windows"]),
            commits_total=g["commits_total"],
            commits_90d=g["commits_90d"],
            commits_30d=g["commits_30d"],
            authors_90d=g["authors_90d"],
            first_commit=g["first_commit"],
            last_commit=g["last_commit"],
            files=[FileStat(**f) for f in g["files"]],
            dirs=[DirStat(**x) for x in g["dirs"]],
            hotspots=[Hotspot(**h) for h in g["hotspots"]],
        )
        return cls(
            sherpa=d["sherpa"],
            schema_version=d["schema_version"],
            repo=d["repo"],
            origin=d["origin"],
            git=git,
            modules=[_module(m) for m in d["modules"]],
            generators=[GeneratorStat(**x) for x in d.get("generators", [])],
            conventions=Conventions(**d["conventions"]),
            coupling=CouplingStats(**d["coupling"]),
        )


def _module(m: dict) -> ModuleStat:
    m = dict(m)
    m["sub_dirs"] = [SubDir(**x) for x in m.get("sub_dirs", [])]
    m["coupling"] = [Coupling(**x) for x in m.get("coupling", [])]
    return ModuleStat(**m)


def load(path: Path) -> Model:
    return Model.from_dict(json.loads(path.read_text(encoding="utf-8")))


def validate(data: dict) -> None:
    """Against the shipped schema with the stdlib validator (ADR-0042); raises ``ValueError`` with the location."""
    from sherpa import schema

    try:
        schema.validate(data, schema.load(SCHEMA_PATH.name))
    except schema.SchemaError as e:
        raise ValueError(f"model invalid at {e.path or 'root'}: {e.message}") from None
