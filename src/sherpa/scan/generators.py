"""Generator families: which files a tool produces, where the source lives, how to regenerate.

Principle (ADR-0011): **Generated code is regenerated, not explained.** The knowledge lives with the generator —
source, configuration, command — not in the output. So a module made of migrations or protobuf stubs gets no
agent; instead the generator's central place gets a skill. For that the scanner reports per family and owning
module: generated files, sources, configuration, ``home`` (common directory) and the regeneration command. All
from paths (T0/T1), without language parsers.

Decisions (owned by this module):
- A path belongs to the **first** family whose glob matches (order in ``FAMILIES``; ``generic`` last).
- A glob without ``/`` matches the file name, one with ``/`` the whole path; ``*`` also matches ``/`` (fnmatch).
- ``GlobSet`` checks each path in constant time instead of families × globs: exact names via dict, ``*<suffix>``
  globs via ``str.endswith``, the rest via anchored regex; path globs only run when their literal (``Migrations/``)
  occurs. 15k paths in ~30 ms — classification must never dominate the git part of the scan.
- ``noise`` (lockfiles, images, data) is not generator output, but is not a hotspot either.
"""

from __future__ import annotations

import posixpath
import re
from collections import defaultdict
from dataclasses import dataclass
from fnmatch import translate
from functools import lru_cache

from sherpa.model import GeneratorStat

MAX_LISTED = 5  # sources/configs per entry in the model (closest to home first)


@dataclass(frozen=True)
class Family:
    id: str
    title: str
    generated: tuple[str, ...]  # output of the generator
    sources: tuple[str, ...]  # the truth the output is generated from
    configs: tuple[str, ...]  # tool configuration
    command: str  # regeneration command or hint
    skill: bool = True  # False: tool-managed, no skill needed


FAMILIES: tuple[Family, ...] = (
    Family(
        "ef-migrations",
        "EF Core Migrations",
        ("*Migrations/[0-9]*_*.cs", "*ModelSnapshot.cs"),  # also a project "X.Migrations/" without a subfolder
        ("*DbContext*.cs",),
        (),
        "dotnet ef migrations add <Name> --project <home>",
    ),
    Family(
        "django-migrations",
        "Django Migrations",
        ("*/migrations/[0-9][0-9][0-9][0-9]_*.py",),
        ("*/models.py", "*/models/*.py"),
        ("manage.py",),
        "python manage.py makemigrations",
    ),
    Family(
        "alembic",
        "Alembic Migrations",
        ("*/alembic/versions/*.py", "*/migrations/versions/*.py"),
        (),
        ("alembic.ini", "*/alembic/env.py"),
        'alembic revision --autogenerate -m "<message>"',
    ),
    Family(
        "protobuf",
        "Protocol Buffers / gRPC",
        (
            "*_pb2.py",
            "*_pb2_grpc.py",
            "*.pb.go",
            "*_grpc.pb.go",
            "*.pb.cc",
            "*.pb.h",
            "*_pb.js",
            "*_pb.d.ts",
            "*.pb.swift",
        ),
        ("*.proto",),
        ("buf.gen.yaml", "buf.yaml", "buf.work.yaml"),
        "buf generate (or protoc with the options from the config)",
    ),
    Family(
        "openapi-client",
        "OpenAPI client generation",
        (),
        (
            "openapi.json",
            "openapi.yaml",
            "openapi.yml",
            "swagger.json",
            "swagger.yaml",
            "*.openapi.json",
            "*.openapi.yaml",
        ),
        (
            "nswag.json",
            "*.nswag",
            "openapi-generator-config.*",
            "*/.openapi-generator/FILES",
            "orval.config.*",
            "kiota-lock.json",
        ),
        "run the generator of the config (nswag run / openapi-generator generate / orval / kiota generate)",
    ),
    Family(
        "graphql-codegen",
        "GraphQL Codegen",
        ("*/__generated__/*",),
        ("*.graphql", "*.gql"),
        ("codegen.yml", "codegen.yaml", "codegen.ts", "codegen.json", "codegen.config.*", "relay.config.*"),
        "graphql-codegen (or relay-compiler)",
    ),
    Family(
        "resx",
        "ResX resources",
        ("*.Designer.cs",),
        ("*.resx",),
        (),
        "the IDE regenerates Designer.cs when the .resx is saved (ResXFileCodeGenerator)",
    ),
    Family(
        "dotnet-codegen",
        ".NET code generation (T4, source generators)",
        ("*.g.cs", "*.g.i.cs", "*.generated.cs"),
        ("*.tt",),
        (),
        "dotnet build (source generators) or TextTransform for .tt templates",
    ),
    Family(
        "go-generate",
        "go generate / mockgen / stringer",
        ("*_string.go", "zz_generated*.go", "mock_*.go", "*_mock.go", "*_gen.go", "*.gen.go", "*_generated.go"),
        (),
        (),
        "go generate ./...",
    ),
    Family(
        "java-codegen",
        "Java code generation (JPA metamodel, MapStruct)",
        ("*_.java", "*MapperImpl.java", "*/generated-sources/*"),
        (),
        (),
        "mvn generate-sources or ./gradlew build",
    ),
    Family(
        "jest-snapshots",
        "test snapshots",
        ("*.snap",),
        (),
        ("jest.config.*", "vitest.config.*"),
        "jest -u or vitest -u",
    ),
    Family(
        "bundles",
        "frontend bundles",
        ("*.min.js", "*.min.css", "*.bundle.js", "*.map"),
        (),
        ("webpack.config.*", "vite.config.*", "rollup.config.*", "esbuild.config.*", "angular.json"),
        "npm run build (build configuration: see configs)",
    ),
    Family(
        "generic",
        "generated files (pattern in the name)",
        (  # *.gen.* only with a code suffix — otherwise it swallows configs such as buf.gen.yaml
            "*.generated.*",
            "*/generated/*",
            "*.gen.ts",
            "*.gen.tsx",
            "*.gen.js",
            "*.gen.cs",
            "*.gen.py",
            "*.gen.rs",
            "*.gen.java",
            "*.gen.kt",
            "*.gen.swift",
            "*.gen.dart",
        ),
        (),
        (),
        "look for the generator in the repo (a script or config next to the sources)",
    ),
    Family(
        "lockfiles",
        "package manager lockfiles",
        (
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "poetry.lock",
            "uv.lock",
            "Cargo.lock",
            "go.sum",
            "Gemfile.lock",
            "composer.lock",
            "packages.lock.json",
        ),
        (),
        (),
        "maintained by the package manager; nothing to regenerate",
        skill=False,
    ),
)

CUSTOM = "custom"  # family for sherpa.toml [scan].generated
NOISE: tuple[str, ...] = ("*.svg", "*.csv", "*.sql.gz", "*.resx")  # never a hotspot, but not generator output

FAMILY_BY_ID = {f.id: f for f in FAMILIES}
GENERATED_GLOBS: tuple[str, ...] = tuple(g for f in FAMILIES for g in f.generated)


_WILD = re.compile(r"[*?\[]")


def _longest_literal(glob: str) -> str:
    return max(_WILD.split(glob), key=len)


class GlobSet:
    """Ordered glob list; ``match`` returns the index of the first matching glob (priority = order)."""

    def __init__(self, globs: tuple[str, ...]) -> None:
        self.globs = globs
        self._exact: dict[str, int] = {}
        self._suffix: dict[str, int] = {}
        name_rx: list[str] = []
        path_rx: list[str] = []
        literals: list[str] = []
        for i, g in enumerate(globs):
            if "/" in g:
                path_rx.append(f"(?P<g{i}>{translate(g)})")
                literals.append(_longest_literal(g))
            elif not _WILD.search(g):
                self._exact.setdefault(g, i)
            elif g.startswith("*") and not _WILD.search(g[1:]):
                self._suffix.setdefault(g[1:], i)
            else:
                name_rx.append(f"(?P<g{i}>{translate(g)})")
        self._suffixes = tuple(self._suffix)
        self._name_rx = re.compile("|".join(name_rx)) if name_rx else None
        self._path_rx = re.compile("|".join(path_rx)) if path_rx else None
        self._path_pre = (
            re.compile("|".join(re.escape(x) for x in sorted(set(literals), key=len, reverse=True) if x))
            if path_rx
            else None
        )

    def match(self, path: str) -> int | None:
        name = path.rsplit("/", 1)[-1]
        hits: list[int] = []
        if (i := self._exact.get(name)) is not None:
            hits.append(i)
        if self._suffixes and name.endswith(self._suffixes):
            hits.append(next(i for suf, i in self._suffix.items() if name.endswith(suf)))
        if self._name_rx and (m := self._name_rx.match(name)):
            hits.append(int(m.lastgroup[1:]))
        if (
            self._path_rx
            and (self._path_pre is None or self._path_pre.search(path))
            and (m := self._path_rx.match(path))
        ):
            hits.append(int(m.lastgroup[1:]))
        return min(hits) if hits else None


@lru_cache(maxsize=64)
def glob_set(globs: tuple[str, ...]) -> GlobSet:
    return GlobSet(globs)


def matches(path: str, globs: tuple[str, ...]) -> bool:
    return bool(globs) and glob_set(globs).match(path) is not None


class Matcher:
    """Path → (family, role) via one ``GlobSet``. Role: ``generated`` | ``source`` | ``config``."""

    def __init__(self, custom: tuple[str, ...] = ()) -> None:
        families = list(FAMILIES)
        if custom:
            families.append(
                Family(CUSTOM, "generated per sherpa.toml", tuple(custom), (), (), "see sherpa.toml [scan].generated")
            )
        # Order = priority: output patterns of all families before sources/configs, so that e.g. a generated
        # *.g.cs is not taken as a source of another family.
        self.tags: list[tuple[str, str]] = []
        globs: list[str] = []
        for role in ("generated", "source", "config"):
            for f in families:
                for g in {"generated": f.generated, "source": f.sources, "config": f.configs}[role]:
                    globs.append(g)
                    self.tags.append((f.id, role))
        self.globset = GlobSet(tuple(globs))
        self.families = {f.id: f for f in families}

    def classify(self, path: str) -> tuple[str, str] | None:
        i = self.globset.match(path)
        return None if i is None else self.tags[i]


def _common_dir(paths: list[str]) -> str:
    dirs = {posixpath.dirname(p) for p in paths}
    if not dirs:
        return ""
    common = posixpath.commonpath(dirs) if len(dirs) > 1 else next(iter(dirs))
    return "" if common == "." else common


def _nearest(paths: list[str], home: str, n: int = MAX_LISTED) -> list[str]:
    """The n paths with the longest common prefix to ``home`` first — sources close to the generator."""

    def shared(p: str) -> int:
        return len(posixpath.commonprefix([posixpath.dirname(p) + "/", home + "/"]))

    return sorted(paths, key=lambda p: (-shared(p), p))[:n]


def detect_generators(
    paths: list[str], locs: dict[str, int | None], owner: dict[str, str | None], matcher: Matcher
) -> tuple[list[GeneratorStat], frozenset[str]]:
    """(generator entries per (family, module), set of all generator outputs)."""
    outputs: dict[tuple[str, str | None], list[str]] = defaultdict(list)
    sources: dict[str, list[str]] = defaultdict(list)
    configs: dict[str, list[str]] = defaultdict(list)
    for p in paths:
        hit = matcher.classify(p)
        if hit is None:
            continue
        fid, role = hit
        if role == "generated":
            outputs[(fid, owner.get(p))].append(p)
        elif role == "source":
            sources[fid].append(p)
        else:
            configs[fid].append(p)

    keys = set(outputs)
    with_output = {k[0] for k in keys}
    for fid in set(sources) | set(
        configs
    ):  # family without output: one entry per module that owns a config (else a source)
        if fid not in with_output:
            for p in configs.get(fid) or sources[fid]:
                keys.add((fid, owner.get(p)))

    stats: list[GeneratorStat] = []
    for fid, mid in sorted(keys, key=lambda k: (k[0], k[1] or "")):
        fam = matcher.families[fid]
        outs = outputs.get((fid, mid), [])
        anchors = outs or [p for p in configs.get(fid) or sources.get(fid, []) if owner.get(p) == mid]
        home = _common_dir(anchors)
        stats.append(
            GeneratorStat(
                family=fid,
                title=fam.title,
                module=mid,
                home=home,
                generated_files=len(outs),
                generated_loc=sum(locs.get(p) or 0 for p in outs),
                sources=_nearest(sources.get(fid, []), home),
                configs=_nearest(configs.get(fid, []), home),
                command=fam.command,
                skill=fam.skill,
            )
        )
    all_outputs = frozenset(p for ps in outputs.values() for p in ps)
    return stats, all_outputs
