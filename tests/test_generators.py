"""Generator families: detection by path, priority, central place, performance structure (GlobSet)."""

from __future__ import annotations

import pytest

from sherpa.config import GENERATED_DEFAULT
from sherpa.scan.generators import FAMILIES, GlobSet, Matcher, detect_generators, glob_set, matches


@pytest.mark.parametrize(
    "path,family,role",
    [
        ("src/Shop.Migrations/20260101120000_Init.cs", "ef-migrations", "generated"),
        ("src/Shop.Migrations/20260101120000_Init.Designer.cs", "ef-migrations", "generated"),  # before resx
        ("src/Shop.Data/Migrations/20260101_Init.cs", "ef-migrations", "generated"),
        ("src/Shop.Data/ShopDbContextModelSnapshot.cs", "ef-migrations", "generated"),
        ("src/Shop.Data/ShopDbContext.cs", "ef-migrations", "source"),
        ("src/Shop.Migrations/MigrationRunner.cs", None, None),  # hand-written code next to migrations
        ("app/shop/migrations/0001_initial.py", "django-migrations", "generated"),
        ("app/shop/models.py", "django-migrations", "source"),
        ("manage.py", "django-migrations", "config"),
        ("db/alembic/versions/abc_init.py", "alembic", "generated"),
        ("alembic.ini", "alembic", "config"),
        ("proto/shop_pb2.py", "protobuf", "generated"),
        ("svc/shop.pb.go", "protobuf", "generated"),
        ("proto/shop.proto", "protobuf", "source"),
        ("buf.gen.yaml", "protobuf", "config"),
        ("api/openapi.json", "openapi-client", "source"),
        ("clients/nswag.json", "openapi-client", "config"),
        ("web/src/__generated__/Query.ts", "graphql-codegen", "generated"),
        ("web/codegen.ts", "graphql-codegen", "config"),
        ("src/A/Properties/Resources.Designer.cs", "resx", "generated"),
        ("src/A/Properties/Resources.resx", "resx", "source"),
        ("src/A/Foo.g.cs", "dotnet-codegen", "generated"),
        ("src/A/Templates/Entity.tt", "dotnet-codegen", "source"),
        ("pkg/kind_string.go", "go-generate", "generated"),
        ("pkg/mock_store.go", "go-generate", "generated"),
        ("src/main/java/Order_.java", "java-codegen", "generated"),
        ("web/__snapshots__/app.test.ts.snap", "jest-snapshots", "generated"),
        ("web/dist/app.min.js", "bundles", "generated"),
        ("web/vite.config.ts", "bundles", "config"),
        ("lib/types.generated.ts", "generic", "generated"),
        ("lib/generated/client.ts", "generic", "generated"),
        ("package-lock.json", "lockfiles", "generated"),
        ("src/Designer/Editor.cs", None, None),
        ("README.md", None, None),
    ],
)
def test_matcher_classifies_by_family_and_role(path, family, role):
    hit = Matcher().classify(path)
    assert hit == ((family, role) if family else None)


def test_custom_globs_form_their_own_family():
    m = Matcher(custom=("gen/*", "*.tpl.out"))
    assert m.classify("gen/out.py") == ("custom", "generated")
    assert m.classify("x/y.tpl.out") == ("custom", "generated")
    assert Matcher().classify("gen/out.py") is None


def test_family_ids_unique_and_lockfiles_without_skill():
    ids = [f.id for f in FAMILIES]
    assert len(ids) == len(set(ids))
    assert next(f for f in FAMILIES if f.id == "lockfiles").skill is False
    assert all(f.skill for f in FAMILIES if f.id != "lockfiles")


def test_globset_priority_is_definition_order():
    gs = GlobSet(("*.Designer.cs", "*Migrations/[0-9]*_*.cs"))
    assert gs.match("src/X.Migrations/20260101_A.Designer.cs") == 0  # the first glob wins
    assert GlobSet(("*Migrations/[0-9]*_*.cs", "*.Designer.cs")).match("src/X.Migrations/20260101_A.Designer.cs") == 0
    assert gs.match("src/Other.cs") is None


def test_globset_name_globs_match_basename_only_and_path_globs_need_literal():
    gs = GlobSet(("mock_*.go", "*/generated/*"))
    assert gs.match("pkg/mock_a.go") == 0 and gs.match("mock_a/b.go") is None
    assert gs.match("lib/generated/x.ts") == 1 and gs.match("lib/gen/x.ts") is None


def test_matches_uses_cached_globset():
    assert matches("a/b.min.js", GENERATED_DEFAULT) and not matches("a/b.js", GENERATED_DEFAULT)
    assert glob_set(GENERATED_DEFAULT) is glob_set(GENERATED_DEFAULT)
    assert not matches("x", ())


def test_detect_generators_groups_by_family_and_owner_module():
    paths = [
        "src/Shop.Migrations/20260101_A.cs",
        "src/Shop.Migrations/20260101_A.Designer.cs",
        "src/Shop.Migrations/ShopDbContextModelSnapshot.cs",
        "src/Shop.Data/ShopDbContext.cs",
        "src/Other/OtherDbContext.cs",
        "api/openapi.json",
        "api/clients/nswag.json",
        "package-lock.json",
        "src/Shop.Data/Service.cs",
    ]
    owner = {
        p: (
            "Shop.Migrations"
            if p.startswith("src/Shop.Migrations/")
            else "Shop.Data"
            if p.startswith("src/Shop.Data/")
            else None
        )
        for p in paths
    }
    owner["api/openapi.json"] = owner["api/clients/nswag.json"] = "Shop.Api"
    locs = {p: 10 for p in paths}
    stats, outputs = detect_generators(paths, locs, owner, Matcher())
    assert outputs == {
        "src/Shop.Migrations/20260101_A.cs",
        "src/Shop.Migrations/20260101_A.Designer.cs",
        "src/Shop.Migrations/ShopDbContextModelSnapshot.cs",
        "package-lock.json",
    }
    by = {(s.family, s.module): s for s in stats}
    ef = by[("ef-migrations", "Shop.Migrations")]
    assert (ef.home, ef.generated_files, ef.generated_loc) == ("src/Shop.Migrations", 3, 30)
    assert ef.sources == ["src/Shop.Data/ShopDbContext.cs", "src/Other/OtherDbContext.cs"]  # closer to home first
    assert ef.command.startswith("dotnet ef migrations add")
    api = by[("openapi-client", "Shop.Api")]  # family without output: entry at the config location
    assert (api.home, api.generated_files, api.configs, api.sources) == (
        "api/clients",
        0,
        ["api/clients/nswag.json"],
        ["api/openapi.json"],
    )
    lock = by[("lockfiles", None)]
    assert (lock.home, lock.skill) == ("", False)
    assert [s.family for s in stats] == sorted(s.family for s in stats)


def test_detect_generators_empty():
    assert detect_generators([], {}, {}, Matcher()) == ([], frozenset())
