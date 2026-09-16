"""Schicht T1: Module aus Manifest-Dateien — sprachunabhängig, deterministisch, ohne Sprach-Parser.

Entscheidungen (Owner dieses Moduls):
- Ein Modul = ein Manifest (``*.csproj``, ``pyproject.toml``, ``package.json``, ``go.mod``, ``Cargo.toml``,
  ``pom.xml``, …). Manifest-Inhalte kommen aus dem Trunk-Rev (``git cat-file``), nie aus dem Working Tree.
- Manifeste unter Werkzeug-Verzeichnissen (``node_modules/``, ``vendor/``, ``target/``, ``bin/``, ``obj/``, …)
  sind keine Module.
- Jede Datei gehört zum **tiefsten** Modul, dessen Verzeichnis sie enthält. Ein Wurzel-Manifest (Pfad ``""``)
  fängt alles, was kein anderes Modul beansprucht.
- ``deps`` enthält nur Abhängigkeiten **innerhalb des Repos** (aufgelöst über Manifest-Pfad oder Modulname);
  externe Pakete sind für Owner-Grenzen irrelevant. ``dependents`` ist die Umkehrung.
- Churn je Modul: ein Commit zählt je Modul einmal, wenn er mindestens eine Datei darin berührt.
- Test-Erkennung: .NET über eigenes Test-Projekt (``tested_by``), sonst über Testdateien im Modul (``test_files``).
"""
from __future__ import annotations

import json
import posixpath
import re
import tomllib
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

from sherpa.model import FileStat, ModuleStat
from sherpa.scan.t0_git import T0Data, blob_contents

SKIP_DIRS = ("node_modules", "vendor", "target", "bin", "obj", "dist", "build", ".venv", "venv",
             "__pycache__", ".git", "packages", "Debug", "Release")

# Manifest-Dateiname → Art. Reihenfolge egal, Erkennung über Dateiname bzw. Endung.
MANIFEST_KINDS: dict[str, str] = {
    "pyproject.toml": "python", "setup.py": "python",
    "package.json": "node",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pom.xml": "java", "build.gradle": "java", "build.gradle.kts": "java",
}
MANIFEST_SUFFIXES: dict[str, str] = {".csproj": "dotnet", ".fsproj": "dotnet", ".vbproj": "dotnet"}

TEST_FILE_GLOBS = ("test_*.py", "*_test.py", "*_test.go", "*.test.js", "*.test.ts", "*.test.tsx",
                   "*.spec.js", "*.spec.ts", "*Test.java", "*Tests.java", "*Test.kt",
                   "*Tests.cs", "*Test.cs", "*_tests.rs", "*_test.rs")
TEST_DIR_NAMES = ("tests", "test", "__tests__", "spec")
DOTNET_TEST_PACKAGES = ("xunit", "nunit", "mstest", "tunit", "microsoft.net.test.sdk")

CI_FILES = (".github/workflows/*", ".gitlab-ci.yml", "azure-pipelines*.yml", "Jenkinsfile",
            ".circleci/config.yml", "bitbucket-pipelines.yml", ".drone.yml")
CONTAINER_FILES = ("Dockerfile", "*.Dockerfile", "docker-compose*.yml", "docker-compose*.yaml", "compose*.yml")

_EXT_LANG = {".cs": "csharp", ".fs": "fsharp", ".vb": "vb", ".py": "python", ".js": "javascript",
             ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript", ".go": "go", ".rs": "rust",
             ".java": "java", ".kt": "kotlin", ".rb": "ruby", ".php": "php", ".swift": "swift",
             ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp", ".sql": "sql", ".sh": "shell",
             ".ps1": "powershell", ".html": "html", ".css": "css", ".scss": "scss", ".md": "markdown",
             ".yml": "yaml", ".yaml": "yaml", ".json": "json", ".xml": "xml", ".toml": "toml"}


@dataclass(frozen=True)
class RawModule:
    id: str
    path: str        # Verzeichnis, "" = Wurzel
    kind: str
    manifest: str
    deps_by_manifest: tuple[str, ...]   # referenzierte Manifest-Pfade (dotnet, rust path-deps)
    deps_by_name: tuple[str, ...]       # referenzierte Modulnamen (python, node, go, java)
    is_test: bool


# --------------------------------------------------------------------------- Manifest-Erkennung

def manifest_kind(path: str) -> str | None:
    parts = path.split("/")
    if any(p in SKIP_DIRS for p in parts[:-1]):
        return None
    name = parts[-1]
    if name in MANIFEST_KINDS:
        return MANIFEST_KINDS[name]
    return MANIFEST_SUFFIXES.get(posixpath.splitext(name)[1])


def _norm_join(base_dir: str, rel: str) -> str:
    rel = rel.replace("\\", "/")
    return posixpath.normpath(posixpath.join(base_dir, rel)) if base_dir else posixpath.normpath(rel)


def _pep503(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _local_xml(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_dotnet(path: str, content: bytes) -> RawModule:
    d = posixpath.dirname(path)
    stem = posixpath.splitext(posixpath.basename(path))[0]
    refs: list[str] = []
    is_test = False
    try:
        root = ET.fromstring(content)
        for el in root.iter():
            tag = _local_xml(el.tag)
            if tag == "ProjectReference" and el.get("Include"):
                refs.append(_norm_join(d, el.get("Include", "")))
            elif tag == "IsTestProject" and (el.text or "").strip().lower() == "true":
                is_test = True
            elif tag == "PackageReference" and (el.get("Include") or "").lower() in DOTNET_TEST_PACKAGES:
                is_test = True
    except ET.ParseError:
        pass
    if re.search(r"\.?Tests?$", stem):
        is_test = True
    return RawModule(stem, d, "dotnet", path, tuple(sorted(set(refs))), (), is_test)


def parse_python(path: str, content: bytes) -> RawModule:
    d = posixpath.dirname(path)
    name, deps = posixpath.basename(d) if d else "root", []
    if path.endswith("pyproject.toml"):
        try:
            data = tomllib.loads(content.decode("utf-8", errors="replace"))
        except tomllib.TOMLDecodeError:
            data = {}
        proj, poetry = data.get("project", {}), data.get("tool", {}).get("poetry", {})
        name = proj.get("name") or poetry.get("name") or name
        for dep in proj.get("dependencies", []):
            deps.append(re.split(r"[\s\[<>=!~;(]", dep, 1)[0])
        for group in proj.get("optional-dependencies", {}).values():
            deps.extend(re.split(r"[\s\[<>=!~;(]", x, 1)[0] for x in group)
        deps.extend(k for k in poetry.get("dependencies", {}) if k != "python")
        for grp in poetry.get("group", {}).values():
            deps.extend(grp.get("dependencies", {}))
    return RawModule(str(name), d, "python", path, (), tuple(sorted({_pep503(x) for x in deps if x})), False)


def parse_node(path: str, content: bytes) -> RawModule:
    d = posixpath.dirname(path)
    try:
        data = json.loads(content.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        data = {}
    name = data.get("name") or (posixpath.basename(d) if d else "root")
    deps = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        deps.update((data.get(key) or {}).keys())
    return RawModule(str(name), d, "node", path, (), tuple(sorted(deps)), False)


def parse_go(path: str, content: bytes) -> RawModule:
    d = posixpath.dirname(path)
    text = content.decode("utf-8", errors="replace")
    m = re.search(r"^module\s+(\S+)", text, re.M)
    name = m.group(1) if m else (posixpath.basename(d) if d else "root")
    deps = set(re.findall(r"^\s*([\w.\-/]+\.[\w.\-/]+)\s+v[\w.\-+]+", text, re.M))     # require-Zeilen
    deps.update(re.findall(r"^\s*replace\s+([\w.\-/]+)\s*=>", text, re.M))
    return RawModule(name, d, "go", path, (), tuple(sorted(deps)), False)


def parse_rust(path: str, content: bytes) -> RawModule | None:
    d = posixpath.dirname(path)
    try:
        data = tomllib.loads(content.decode("utf-8", errors="replace"))
    except tomllib.TOMLDecodeError:
        data = {}
    pkg = data.get("package")
    if not pkg:
        return None                                   # reiner [workspace]-Root ist kein Modul
    by_manifest, by_name = [], []
    for key in ("dependencies", "dev-dependencies", "build-dependencies"):
        for dep_name, spec in (data.get(key) or {}).items():
            if isinstance(spec, dict) and "path" in spec:
                by_manifest.append(posixpath.join(_norm_join(d, spec["path"]), "Cargo.toml"))
            else:
                by_name.append(dep_name)
    return RawModule(str(pkg.get("name") or posixpath.basename(d)), d, "rust", path,
                     tuple(sorted(set(by_manifest))), tuple(sorted(set(by_name))), False)


def parse_java(path: str, content: bytes) -> RawModule | None:
    d = posixpath.dirname(path)
    if not path.endswith("pom.xml"):
        return RawModule(posixpath.basename(d) if d else "root", d, "java", path, (), (), False)
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return RawModule(posixpath.basename(d) if d else "root", d, "java", path, (), (), False)
    def child(el, tag):
        for c in el:
            if _local_xml(c.tag) == tag:
                return c
        return None
    art = child(root, "artifactId")
    name = (art.text or "").strip() if art is not None else (posixpath.basename(d) if d else "root")
    deps = []
    deps_el = child(root, "dependencies")
    if deps_el is not None:
        for dep in deps_el:
            a = child(dep, "artifactId")
            if a is not None and a.text:
                deps.append(a.text.strip())
    return RawModule(name, d, "java", path, (), tuple(sorted(set(deps))), False)


PARSERS = {"dotnet": parse_dotnet, "python": parse_python, "node": parse_node,
           "go": parse_go, "rust": parse_rust, "java": parse_java}


def find_modules(paths: list[str], contents: dict[str, bytes | None]) -> list[RawModule]:
    mods: list[RawModule] = []
    for p in paths:
        kind = manifest_kind(p)
        if kind is None or contents.get(p) is None:
            continue
        m = PARSERS[kind](p, contents[p] or b"")
        if m is not None:
            mods.append(m)
    # Ein Verzeichnis, mehrere Manifeste (pyproject + package.json): erstes nach Pfad gewinnt.
    seen: set[str] = set()
    out = []
    for m in sorted(mods, key=lambda m: (m.path, m.manifest)):
        if m.path in seen:
            continue
        seen.add(m.path)
        out.append(m)
    return out


# --------------------------------------------------------------------------- Auflösung + Aggregation

def is_test_file(path: str) -> bool:
    parts = path.split("/")
    if any(p in TEST_DIR_NAMES for p in parts[:-1]):
        return True
    return any(fnmatchcase(parts[-1], g) for g in TEST_FILE_GLOBS)


def assign_files(paths: list[str], modules: list[RawModule]) -> dict[str, str | None]:
    """Datei → Modul-id (tiefstes Modul); None, wenn kein Modul zuständig."""
    by_depth = sorted(modules, key=lambda m: -len(m.path))
    out: dict[str, str | None] = {}
    for p in paths:
        out[p] = None
        for m in by_depth:
            if m.path == "" or p.startswith(m.path + "/"):
                out[p] = m.id
                break
    return out


def resolve_deps(modules: list[RawModule]) -> dict[str, list[str]]:
    by_manifest = {m.manifest: m.id for m in modules}
    by_manifest_ci = {k.lower(): v for k, v in by_manifest.items()}
    by_name: dict[str, str] = {}
    for m in modules:
        by_name[m.id] = m.id
        by_name[_pep503(m.id)] = m.id
    out: dict[str, list[str]] = {}
    for m in modules:
        deps: set[str] = set()
        for ref in m.deps_by_manifest:
            hit = by_manifest.get(ref) or by_manifest_ci.get(ref.lower())
            if hit is None:                            # Fallback: Projektname = Dateistamm
                hit = by_name.get(posixpath.splitext(posixpath.basename(ref))[0])
            if hit and hit != m.id:
                deps.add(hit)
        for name in m.deps_by_name:
            hit = by_name.get(name) or by_name.get(_pep503(name))
            if hit and hit != m.id:
                deps.add(hit)
        out[m.id] = sorted(deps)
    return out


def build_modules(data: T0Data, files: list[FileStat], contents: dict[str, bytes | None], *,
                  hotspots_per_module: int = 3) -> list[ModuleStat]:
    paths = list(data.paths)
    raw = find_modules(paths, contents)
    if not raw:
        return []
    owner = assign_files(paths, raw)
    deps = resolve_deps(raw)
    dependents: dict[str, list[str]] = defaultdict(list)
    for mid, ds in deps.items():
        for d in ds:
            dependents[d].append(mid)
    tested_by: dict[str, list[str]] = defaultdict(list)
    for m in raw:
        if m.is_test:
            for d in deps[m.id]:
                tested_by[d].append(m.id)

    fstat = {f.path: f for f in files}
    nfiles: dict[str, int] = defaultdict(int)
    loc: dict[str, int] = defaultdict(int)
    tfiles: dict[str, int] = defaultdict(int)
    scored: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for p, mid in owner.items():
        if mid is None:
            continue
        f = fstat[p]
        nfiles[mid] += 1
        loc[mid] += f.loc or 0
        if is_test_file(p):
            tfiles[mid] += 1
        if f.commits_90d >= 1 and f.loc is not None and not f.generated:
            scored[mid].append((-(f.commits_90d * f.loc), p))

    c90: dict[str, set[str]] = defaultdict(set)
    c30: dict[str, set[str]] = defaultdict(set)
    authors: dict[str, set[str]] = defaultdict(set)
    for c in data.commits:
        touched = {owner[f] for f in c.files if owner.get(f)}
        for mid in touched:
            c90[mid].add(c.sha)
            authors[mid].add(c.author)
            if c.date > data.since_30:
                c30[mid].add(c.sha)

    return [
        ModuleStat(
            id=m.id, path=m.path, kind=m.kind, manifest=m.manifest, is_test=m.is_test,
            files=nfiles[m.id], loc=loc[m.id], test_files=tfiles[m.id],
            deps=deps[m.id], dependents=sorted(dependents[m.id]), tested_by=sorted(tested_by[m.id]),
            commits_90d=len(c90[m.id]), commits_30d=len(c30[m.id]), authors_90d=len(authors[m.id]),
            hotspots=[p for _, p in sorted(scored[m.id])[:hotspots_per_module]],
        )
        for m in sorted(raw, key=lambda m: (m.path, m.id))
    ]


def detect_conventions(paths: list[str], locs: dict[str, int | None]) -> tuple[dict[str, int], list[str], list[str]]:
    """(Sprachen nach LOC, CI-Dateien, Container-Dateien) — alles aus dem Dateibaum."""
    langs: dict[str, int] = defaultdict(int)
    ci, containers = [], []
    for p in paths:
        lang = _EXT_LANG.get(posixpath.splitext(p)[1].lower())
        if lang and locs.get(p):
            langs[lang] += locs[p] or 0
        name = p.rsplit("/", 1)[-1]
        if any(fnmatchcase(p, g) or fnmatchcase(name, g) for g in CI_FILES):
            ci.append(p)
        elif any(fnmatchcase(name, g) for g in CONTAINER_FILES):
            containers.append(p)
    return dict(sorted(langs.items(), key=lambda kv: (-kv[1], kv[0]))), ci, containers


def manifest_paths(paths: list[str]) -> list[str]:
    return [p for p in paths if manifest_kind(p)]


def load_manifests(repo: Path, ref: str, paths: list[str]) -> dict[str, bytes | None]:
    return blob_contents(repo, ref, manifest_paths(paths))
