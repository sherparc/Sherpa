"""T1 on a programmatic polyglot fixture: dotnet, python, node, go, rust, java in ONE repo.

Expected module landscape (path → id, deps within the repo):
  src/Shop.Core/Shop.Core.csproj                 Shop.Core
  src/Shop.Pricing/Shop.Pricing.csproj           Shop.Pricing      → Shop.Core
  tests/Shop.Pricing.Tests/….csproj              Shop.Pricing.Tests → Shop.Pricing, Shop.Core (is_test)
  py/lib/pyproject.toml                          shop-lib
  py/app/pyproject.toml                          shop-app          → shop-lib (PEP 503 normalisation of "Shop_Lib")
  web/package.json                               @shop/web         → @shop/ui  (devDependency)
  web/ui/package.json                            @shop/ui
  web/node_modules/left-pad/package.json         (ignored)
  go/svc/go.mod                                  example.com/shop/svc → example.com/shop/lib (require)
  go/lib/go.mod                                  example.com/shop/lib
  rust/Cargo.toml                                [workspace] (not a module)
  rust/core/Cargo.toml                           shop-core-rs
  rust/cli/Cargo.toml                            shop-cli          → shop-core-rs (path-dep)
  java/pom.xml                                   shop-parent
  java/api/pom.xml                               shop-api          → shop-domain (artifactId)
  java/domain/pom.xml                            shop-domain
"""

from __future__ import annotations

import shutil
from datetime import UTC
from pathlib import Path

import pytest

from sherpa.gitinfo import resolve_trunk
from sherpa.model import Coupling, CouplingStats, FileStat
from sherpa.scan import scan
from sherpa.scan.t0_git import collect
from sherpa.scan.t1_modules import (
    assign_files,
    build_modules,
    compute_coupling,
    coupling_cap,
    detect_conventions,
    find_modules,
    is_test_file,
    load_manifests,
    manifest_kind,
    parse_dotnet,
    parse_go,
    parse_java,
    parse_node,
    parse_python,
    parse_rust,
    resolve_deps,
)
from tests.conftest import commit, git

CSPROJ = '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup>{body}</Project>'
D1, D2 = "2026-01-15T12:00:00Z", "2026-02-20T12:00:00Z"

FILES: dict[str, str | bytes] = {
    "src/Shop.Core/Shop.Core.csproj": CSPROJ.format(body=""),
    "src/Shop.Core/Money.cs": "class Money {}\n",
    "src/Shop.Pricing/Shop.Pricing.csproj": CSPROJ.format(
        body='<ItemGroup><ProjectReference Include="..\\Shop.Core\\Shop.Core.csproj" /></ItemGroup>'
    ),
    "src/Shop.Pricing/PriceEngine.cs": "class PriceEngine {}\n",
    "src/Shop.Pricing/Properties/Resources.Designer.cs": "// generated\n" * 50,
    "tests/Shop.Pricing.Tests/Shop.Pricing.Tests.csproj": CSPROJ.format(
        body='<ItemGroup><PackageReference Include="xunit" Version="2.9" />'
        '<ProjectReference Include="../../src/Shop.Pricing/Shop.Pricing.csproj" />'
        '<ProjectReference Include="../../src/Shop.Core/Shop.Core.csproj" /></ItemGroup>'
    ),
    "tests/Shop.Pricing.Tests/PriceEngineTests.cs": "class PriceEngineTests {}\n",
    "py/lib/pyproject.toml": '[project]\nname = "Shop_Lib"\nversion = "0"\n',
    "py/lib/shop_lib/__init__.py": "",
    "py/app/pyproject.toml": '[project]\nname = "shop-app"\nversion = "0"\ndependencies = ["shop-lib>=0", "requests"]\n'
    '[project.optional-dependencies]\ndev = ["pytest"]\n',
    "py/app/shop_app/main.py": "print(1)\n",
    "py/app/tests/test_main.py": "def test_x(): pass\n",
    "web/package.json": '{"name": "@shop/web", "devDependencies": {"@shop/ui": "*", "vite": "5"}}',
    "web/src/app.ts": "export {}\n",
    "web/src/app.test.ts": "test('x', () => {})\n",
    "web/ui/package.json": '{"name": "@shop/ui", "dependencies": {"react": "18"}}',
    "web/ui/index.ts": "export {}\n",
    "web/node_modules/left-pad/package.json": '{"name": "left-pad"}',
    "web/node_modules/left-pad/index.js": "x\n",
    "go/svc/go.mod": "module example.com/shop/svc\n\ngo 1.22\n\nrequire (\n\texample.com/shop/lib v0.0.0\n\tgithub.com/x/y v1.2.3\n)\n"
    "\nreplace example.com/shop/lib => ../lib\n",
    "go/svc/main.go": "package main\n",
    "go/svc/main_test.go": "package main\n",
    "go/lib/go.mod": "module example.com/shop/lib\n\ngo 1.22\n",
    "go/lib/lib.go": "package lib\n",
    "rust/Cargo.toml": '[workspace]\nmembers = ["core", "cli"]\n',
    "rust/core/Cargo.toml": '[package]\nname = "shop-core-rs"\nversion = "0.1.0"\n',
    "rust/core/src/lib.rs": "pub fn f() {}\n",
    "rust/cli/Cargo.toml": '[package]\nname = "shop-cli"\nversion = "0.1.0"\n[dependencies]\nshop-core-rs = { path = "../core" }\nserde = "1"\n',
    "rust/cli/src/main.rs": "fn main() {}\n",
    "java/pom.xml": '<project xmlns="http://maven.apache.org/POM/4.0.0"><artifactId>shop-parent</artifactId>'
    "<packaging>pom</packaging><modules><module>api</module><module>domain</module></modules></project>",
    "java/api/pom.xml": "<project><artifactId>shop-api</artifactId><dependencies>"
    "<dependency><groupId>x</groupId><artifactId>shop-domain</artifactId></dependency>"
    "<dependency><groupId>org.junit</groupId><artifactId>junit</artifactId></dependency>"
    "</dependencies></project>",
    "java/api/src/main/java/Api.java": "class Api {}\n",
    "java/api/src/test/java/ApiTest.java": "class ApiTest {}\n",
    "java/domain/pom.xml": "<project><artifactId>shop-domain</artifactId></project>",
    "java/domain/src/main/java/Domain.java": "class Domain {}\n",
    ".github/workflows/ci.yml": "on: push\n",
    "Dockerfile": "FROM scratch\n",
    "docs/README.md": "# docs\n",
}


def build_poly_repo(tmp_path: Path) -> Path:
    work = tmp_path / "seed"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    commit(work, "c1", FILES, date=D1, author="A")
    commit(
        work,
        "c2",
        {
            "src/Shop.Pricing/PriceEngine.cs": "class PriceEngine { int x; }\n",
            "src/Shop.Core/Money.cs": "class Money { int v; }\n",
        },
        date=D2,
        author="B",
    )
    commit(
        work,
        "c3",
        {"src/Shop.Pricing/PriceEngine.cs": "class PriceEngine { int x, y; }\n"},
        date="2026-03-01T12:00:00Z",
        author="A",
    )
    origin = tmp_path / "origin.git"
    git(tmp_path, "clone", "-q", "--bare", str(work), str(origin))
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(origin), str(clone))
    return clone


# ---------------------------------------------------------------- detection


@pytest.mark.parametrize(
    "path,kind",
    [
        ("src/A/A.csproj", "dotnet"),
        ("x/y.fsproj", "dotnet"),
        ("pyproject.toml", "python"),
        ("setup.py", "python"),
        ("web/package.json", "node"),
        ("go.mod", "go"),
        ("Cargo.toml", "rust"),
        ("pom.xml", "java"),
        ("app/build.gradle.kts", "java"),
        ("web/node_modules/x/package.json", None),
        ("rust/target/debug/Cargo.toml", None),
        ("src/A/bin/Debug/A.csproj", None),
        ("README.md", None),
        ("src/A/A.csproj.user", None),
    ],
)
def test_manifest_kind(path, kind):
    assert manifest_kind(path) == kind


@pytest.mark.parametrize(
    "path,expected",
    [
        ("tests/x.cs", True),
        ("a/test/b.py", True),
        ("a/__tests__/b.js", True),
        ("spec/x.rb", True),
        ("pkg/test_x.py", True),
        ("pkg/x_test.py", True),
        ("cmd/x_test.go", True),
        ("web/a.test.ts", True),
        ("web/a.spec.js", True),
        ("src/FooTest.java", True),
        ("src/FooTests.cs", True),
        ("src/x_tests.rs", True),
        ("src/Foo.cs", False),
        ("src/testing/Foo.cs", False),
        ("contest/x.py", False),
    ],
)
def test_is_test_file(path, expected):
    assert is_test_file(path) is expected


# ---------------------------------------------------------------- Parser


def test_parse_dotnet_refs_and_test_detection():
    m = parse_dotnet(
        "tests/Shop.Pricing.Tests/Shop.Pricing.Tests.csproj",
        FILES["tests/Shop.Pricing.Tests/Shop.Pricing.Tests.csproj"].encode(),
    )
    assert m.id == "Shop.Pricing.Tests" and m.path == "tests/Shop.Pricing.Tests" and m.is_test
    assert m.deps_by_manifest == ("src/Shop.Core/Shop.Core.csproj", "src/Shop.Pricing/Shop.Pricing.csproj")


def test_parse_dotnet_backslash_ref_and_is_test_property():
    m = parse_dotnet("src/Shop.Pricing/Shop.Pricing.csproj", FILES["src/Shop.Pricing/Shop.Pricing.csproj"].encode())
    assert m.deps_by_manifest == ("src/Shop.Core/Shop.Core.csproj",) and not m.is_test
    m2 = parse_dotnet(
        "t/X/X.csproj",
        CSPROJ.format(body="<PropertyGroup><IsTestProject>true</IsTestProject></PropertyGroup>").encode(),
    )
    assert m2.is_test
    m3 = parse_dotnet("t/X/X.csproj", b"<not xml")
    assert m3.id == "X" and m3.deps_by_manifest == ()


def test_parse_python_normalises_names():
    m = parse_python("py/app/pyproject.toml", FILES["py/app/pyproject.toml"].encode())
    assert m.id == "shop-app" and m.deps_by_name == ("pytest", "requests", "shop-lib")
    lib = parse_python("py/lib/pyproject.toml", FILES["py/lib/pyproject.toml"].encode())
    assert lib.id == "Shop_Lib"
    poetry = parse_python(
        "p/pyproject.toml", b'[tool.poetry]\nname="p"\n[tool.poetry.dependencies]\npython="^3.12"\nq="1"\n'
    )
    assert poetry.id == "p" and poetry.deps_by_name == ("q",)
    assert parse_python("setup.py", b"").id == "root"
    assert parse_python("x/pyproject.toml", b"not = toml = bad").id == "x"


def test_parse_node():
    m = parse_node("web/package.json", FILES["web/package.json"].encode())
    assert m.id == "@shop/web" and m.deps_by_name == ("@shop/ui", "vite")
    assert parse_node("web/package.json", b"{bad").id == "web"


def test_parse_go():
    m = parse_go("go/svc/go.mod", FILES["go/svc/go.mod"].encode())
    assert m.id == "example.com/shop/svc"
    assert m.deps_by_name == ("example.com/shop/lib", "github.com/x/y")


def test_parse_rust_workspace_root_is_not_a_module():
    assert parse_rust("rust/Cargo.toml", FILES["rust/Cargo.toml"].encode()) is None
    m = parse_rust("rust/cli/Cargo.toml", FILES["rust/cli/Cargo.toml"].encode())
    assert m.id == "shop-cli" and m.deps_by_manifest == ("rust/core/Cargo.toml",) and m.deps_by_name == ("serde",)
    assert parse_rust("x/Cargo.toml", b"[package\nbad") is None


def test_parse_java():
    m = parse_java("java/api/pom.xml", FILES["java/api/pom.xml"].encode())
    assert m.id == "shop-api" and m.deps_by_name == ("junit", "shop-domain")
    assert parse_java("java/pom.xml", FILES["java/pom.xml"].encode()).id == "shop-parent"  # namespaced XML
    assert parse_java("g/build.gradle", b"").id == "g"
    assert parse_java("b/pom.xml", b"<bad").id == "b"


# ---------------------------------------------------------------- resolution


def test_find_modules_one_per_dir_and_skips_tool_dirs():
    paths = sorted(FILES)
    contents = {p: (v.encode() if isinstance(v, str) else v) for p, v in FILES.items()}
    mods = find_modules(paths, contents)
    ids = {m.id for m in mods}
    assert "left-pad" not in ids and "shop-parent" in ids
    assert len(mods) == 14
    two = {"x/pyproject.toml": b'[project]\nname="a"\n', "x/package.json": b'{"name":"b"}'}
    assert [m.id for m in find_modules(sorted(two), two)] == ["b"]  # no source files: the manifest name decides


def test_find_modules_two_manifests_the_language_with_more_files_wins():
    """ADR-0025: a root with pyproject.toml and package.json is the ecosystem of its files, not of the alphabet."""
    two = {"pyproject.toml": b'[project]\nname="svc"\n', "package.json": b'{"name":"web"}'}
    paths = sorted(two) + [f"svc/m{i}.py" for i in range(5)] + ["web/app.ts", "web/index.tsx"]
    (m,) = find_modules(paths, two)
    assert (m.id, m.kind, m.manifest) == ("svc", "python", "pyproject.toml")
    paths = sorted(two) + ["svc/m.py"] + [f"web/c{i}.ts" for i in range(3)]
    (m,) = find_modules(paths, two)
    assert (m.id, m.kind) == ("web", "node")
    paths = sorted(two) + ["svc/m.py", "web/c.ts"]  # a tie: the manifest name decides, deterministically
    assert find_modules(paths, two)[0].id == "web"


def test_assign_files_deepest_module_wins_and_root_catches_rest():
    from sherpa.scan.t1_modules import RawModule

    root = RawModule("root", "", "node", "package.json", (), (), False)
    sub = RawModule("sub", "pkg/sub", "node", "pkg/sub/package.json", (), (), False)
    got = assign_files(["a.txt", "pkg/sub/x.js", "pkg/other.js"], [root, sub])
    assert got == {"a.txt": "root", "pkg/sub/x.js": "sub", "pkg/other.js": "root"}
    assert assign_files(["a.txt"], [sub]) == {"a.txt": None}


def test_resolve_deps_cross_language_rules():
    paths = sorted(FILES)
    contents = {p: (v.encode() if isinstance(v, str) else v) for p, v in FILES.items()}
    deps = resolve_deps(find_modules(paths, contents))
    assert deps["Shop.Pricing"] == ["Shop.Core"]
    assert deps["Shop.Pricing.Tests"] == ["Shop.Core", "Shop.Pricing"]
    assert deps["shop-app"] == ["Shop_Lib"]  # PEP 503: shop-lib ≙ Shop_Lib
    assert deps["@shop/web"] == ["@shop/ui"]
    assert deps["example.com/shop/svc"] == ["example.com/shop/lib"]
    assert deps["shop-cli"] == ["shop-core-rs"]
    assert deps["shop-api"] == ["shop-domain"]
    assert deps["Shop.Core"] == [] and deps["shop-parent"] == []


def test_resolve_deps_manifest_fallback_by_stem():
    from sherpa.scan.t1_modules import RawModule

    a = RawModule("A", "src/A", "dotnet", "src/A/A.csproj", ("wrong/path/B.csproj",), (), False)
    b = RawModule("B", "lib/B", "dotnet", "lib/B/B.csproj", (), (), False)
    assert resolve_deps([a, b])["A"] == ["B"]


# ---------------------------------------------------------------- end to end


def test_build_modules_on_poly_repo(poly_repo: Path):
    m = scan(poly_repo, fetch=False)
    by = {x.id: x for x in m.modules}
    assert len(m.modules) == 14
    assert [x.id for x in m.modules] == sorted((x.id for x in m.modules), key=lambda i: (by[i].path, i))

    pricing = by["Shop.Pricing"]
    assert (pricing.kind, pricing.path, pricing.files, pricing.is_test) == ("dotnet", "src/Shop.Pricing", 3, False)
    assert pricing.deps == ["Shop.Core"] and pricing.dependents == ["Shop.Pricing.Tests"]
    assert pricing.tested_by == ["Shop.Pricing.Tests"]
    assert (pricing.commits_90d, pricing.commits_30d, pricing.authors_90d) == (3, 2, 2)
    # Designer.cs is generated → no hotspot; csproj has 1 commit × 1 LOC → last
    assert pricing.hotspots == ["src/Shop.Pricing/PriceEngine.cs", "src/Shop.Pricing/Shop.Pricing.csproj"]
    assert pricing.loc == 50 + 1 + 1  # LOC including the generated file

    core = by["Shop.Core"]
    assert core.dependents == ["Shop.Pricing", "Shop.Pricing.Tests"] and core.tested_by == ["Shop.Pricing.Tests"]
    assert (core.commits_90d, core.commits_30d) == (2, 1)

    tests = by["Shop.Pricing.Tests"]
    assert tests.is_test and tests.test_files == 2  # csproj + Tests.cs live under tests/

    assert by["shop-app"].test_files == 1 and by["@shop/web"].test_files == 1
    assert by["example.com/shop/svc"].test_files == 1 and by["shop-api"].test_files == 1
    assert by["Shop_Lib"].commits_90d == 1 and by["Shop_Lib"].commits_30d == 0

    assert m.conventions.ci == [".github/workflows/ci.yml"] and m.conventions.containers == ["Dockerfile"]
    assert list(m.conventions.languages)[0] == "csharp"


def test_files_outside_modules_are_not_counted(poly_repo: Path):
    m = scan(poly_repo, fetch=False)
    assert sum(x.files for x in m.modules) < len(m.git.files)  # docs/, Dockerfile, .github/ belong to no module


def test_no_manifests_gives_empty_modules(make_origin, make_clone):
    origin, _ = make_origin()
    clone = make_clone(origin)
    m = scan(clone, fetch=False)
    assert m.modules == [] and m.conventions.languages == {} and m.conventions.ci == []


def test_load_manifests_reads_only_manifests(poly_repo: Path):
    t = resolve_trunk(poly_repo)
    data = collect(poly_repo, t)
    contents = load_manifests(poly_repo, t.rev, list(data.paths))
    assert "src/Shop.Core/Shop.Core.csproj" in contents and "src/Shop.Core/Money.cs" not in contents
    assert "web/node_modules/left-pad/package.json" not in contents


def test_build_modules_direct_with_empty_files():
    from datetime import datetime

    from sherpa.gitinfo import Trunk
    from sherpa.scan.t0_git import T0Data

    now = datetime(2026, 1, 1, tzinfo=UTC)
    data = T0Data(Trunk("origin/main", "candidate", "0" * 40), now, now, now, (), (), {})
    assert build_modules(data, [], {}) == []


def test_detect_conventions_counts_loc_per_language():
    langs, ci, containers = detect_conventions(
        ["a.cs", "b.cs", "c.py", "d.bin", "Jenkinsfile", "ops/docker-compose.prod.yml", "x.Dockerfile"],
        {
            "a.cs": 10,
            "b.cs": 5,
            "c.py": 7,
            "d.bin": None,
            "Jenkinsfile": 1,
            "ops/docker-compose.prod.yml": 1,
            "x.Dockerfile": 1,
        },
    )
    assert list(langs.items()) == [("csharp", 15), ("python", 7), ("yaml", 1)]
    assert ci == ["Jenkinsfile"] and containers == ["ops/docker-compose.prod.yml", "x.Dockerfile"]


def test_scan_stays_deterministic_with_modules(poly_repo: Path):
    assert scan(poly_repo, fetch=False).to_json() == scan(poly_repo, fetch=False).to_json()


# ---------------------------------------------------------------- model v4: coupling and sub-directories (ADR-0020/0021)


def _data(commits):
    from datetime import datetime, timedelta

    from sherpa.gitinfo import Trunk
    from sherpa.scan.t0_git import Commit, T0Data

    now = datetime(2026, 3, 1, tzinfo=UTC)
    cs = tuple(Commit(f"{i:040x}", a, now - timedelta(days=d), tuple(files)) for i, (a, d, files) in enumerate(commits))
    return T0Data(
        Trunk("origin/main", "candidate", "0" * 40), now, now - timedelta(days=90), now - timedelta(days=30), cs, (), {}
    )


def test_coupling_cap_and_floors():
    assert coupling_cap(1) == 5 and coupling_cap(10) == 5 and coupling_cap(11) == 6 and coupling_cap(122) == 61
    owner = {"a/x": "A", "b/x": "B", "c/x": "C", "d/x": "D", "e/x": "E", "f/x": "F", "g/x": "G", "n/x": None}
    commits = [("u", 1, ["a/x", "b/x"])] * 6  # A and B change together six times
    commits += [("u", 2, ["a/x"])] * 4  # A alone: A has 10 commits, B 6 → share A→B 0.6, B→A 1.0
    commits += [("u", 3, ["a/x", "c/x"])] * 2  # below min_shared 5
    commits += [("u", 4, ["a/x", "b/x", "c/x", "d/x", "e/x", "f/x", "g/x"])] * 3  # 7 modules > cap 5: skipped
    commits += [("u", 5, ["n/x"])]  # no module: ignored, not counted
    per, stats = compute_coupling(_data(commits), owner, list("ABCDEFG"))
    assert stats == CouplingStats(cap=5, skipped_commits=3, measured_commits=12, min_shared=5, min_share=0.3)
    assert per["A"] == [Coupling("B", 6, 0.5)]  # 6 of A's 12 measured commits
    assert per["B"] == [Coupling("A", 6, 1.0)] and per["C"] == [] and per["G"] == []


def test_coupling_excludes_the_root_catch_all(poly_repo: Path):
    """ADR-0026: the root module owns everything no other manifest claims; a partner row naming it says only
    "touches the rest". Excluded from partners and from the cap count of a commit; the model records which."""
    owner = {"a/x": "A", "b/x": "B", "README.md": "ROOT", "docs/y": "ROOT"}
    commits = [("u", 1, ["a/x", "b/x", "README.md"])] * 6 + [("u", 2, ["a/x", "docs/y"])] * 4
    per, stats = compute_coupling(_data(commits), owner, ["ROOT", "A", "B"])
    assert per["A"] == [Coupling("ROOT", 10, 1.0), Coupling("B", 6, 0.6)]  # without the exclusion
    per, stats = compute_coupling(_data(commits), owner, ["ROOT", "A", "B"], exclude="ROOT")
    assert per["A"] == [Coupling("B", 6, 0.6)] and per["ROOT"] == [] and stats.excluded == "ROOT"
    assert scan(poly_repo, fetch=False).coupling.excluded is None  # no root manifest there: nothing to exclude


def test_scan_excludes_the_root_module_only_next_to_others(tmp_path: Path, make_origin, make_clone):
    origin, _ = make_origin()
    seed = tmp_path / "seed"
    commit(seed, "root package", {"pyproject.toml": '[project]\nname = "svc"\n', "svc/a.py": "x\n"})
    git(seed, "push", "-q", str(origin), "main")
    assert scan(make_clone(origin), fetch=False).coupling.excluded is None  # alone: a real unit, measured
    commit(seed, "a web module", {"web/package.json": '{"name": "web"}', "web/i.ts": "y\n"})
    git(seed, "push", "-q", str(origin), "main")
    clone = tmp_path / "clone"
    shutil.rmtree(clone)
    m = scan(make_clone(origin), fetch=False)
    assert m.coupling.excluded == "svc" and [x.id for x in m.modules] == ["svc", "web"]


def test_coupling_top_three_ordered_by_shared_then_name():
    owner = {f"{m}/x": m for m in "ABCDF"}
    commits = [("u", 1, ["A/x", "B/x", "C/x", "D/x", "F/x"])] * 10  # five modules = the cap, still measured
    commits += [("u", 1, ["A/x", "B/x"])] * 2 + [("u", 1, ["A/x", "C/x"])]
    per, stats = compute_coupling(_data(commits), owner, list("ABCDF"))
    assert stats.skipped_commits == 0
    assert [(c.module, c.shared) for c in per["A"]] == [("B", 12), ("C", 11), ("D", 10)]  # F ties D, name order


def test_sub_dirs_depth_source_files_package_and_commits():
    from sherpa.scan.t1_modules import RawModule, sub_dirs_of

    paths = [
        "src/pkg/__init__.py",
        "src/pkg/a/__init__.py",
        "src/pkg/a/one.py",
        "src/pkg/a/deep/x/y/z.py",
        "src/pkg/b/README.md",
        "docs/guide.md",
        "setup.cfg",
    ]
    fstat = {p: FileStat(p, 10, False, 0, 0, 0, None) for p in paths}
    data = _data([("u", 1, ["src/pkg/a/one.py"]), ("v", 40, ["src/pkg/a/one.py", "src/pkg/b/README.md"])])
    m = RawModule("pkg", "", "python", "pyproject.toml", (), (), False)
    subs = {s.path: s for s in sub_dirs_of(m, paths, fstat, data)}
    assert set(subs) == {"src", "src/pkg", "src/pkg/a", "src/pkg/a/deep", "src/pkg/b", "docs"}  # depth ≤ 4
    a = subs["src/pkg/a"]
    assert (a.depth, a.files, a.source_files, a.package, a.loc) == (3, 3, 3, True, 30)
    assert (a.commits_90d, a.commits_30d, a.authors_90d) == (2, 1, 2)
    assert subs["src/pkg/b"].package is False and subs["src/pkg/b"].source_files == 0
    assert subs["src"].package is False and subs["src"].files == 5
    # a nested module: paths outside it are not its sub-directories
    nested = RawModule("a", "src/pkg/a", "python", "src/pkg/a/pyproject.toml", (), (), False)
    assert [s.path for s in sub_dirs_of(nested, paths, fstat, data)] == [
        "src/pkg/a/deep",
        "src/pkg/a/deep/x",
        "src/pkg/a/deep/x/y",
    ]


def test_scan_carries_sub_dirs_and_coupling_stats(poly_repo: Path):
    m = scan(poly_repo, fetch=False)
    assert m.coupling.cap == 7 and m.coupling.min_shared == 5  # 14 modules → ceil(14/2)
    assert all(c.shared >= 5 for x in m.modules for c in x.coupling)
    pricing = next(x for x in m.modules if x.id == "Shop.Pricing")
    assert pricing.sub_dirs == [] or all(s.path.startswith("src/Shop.Pricing/") for s in pricing.sub_dirs)
