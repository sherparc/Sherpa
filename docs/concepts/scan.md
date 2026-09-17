# `sherpa scan` — layers T0 (git), T1 (modules) and generator families

> Owner of: invocation, decisions, interpretation. Field semantics belong to the schema
> [`src/sherpa/schemas/codebase-model.schema.json`](../../src/sherpa/schemas/codebase-model.schema.json) (v3); code in
> [`src/sherpa/scan/t0_git.py`](../../src/sherpa/scan/t0_git.py), [`t1_modules.py`](../../src/sherpa/scan/t1_modules.py)
> and [`generators.py`](../../src/sherpa/scan/generators.py). Status: M3d, v0.6.0 (model schema 4).

Command reference (options, exit codes, troubleshooting): [`sherpa scan`](../commands/scan.md).

## Invocation

```bash
sherpa scan <repo>                      # → <repo>/.sherpa/codebase-model.json
sherpa scan <repo> --out -              # JSON to stdout
sherpa scan <repo> --no-fetch           # without 'git fetch origin' (offline, tests)
sherpa scan <repo> --trunk dev          # force the trunk (beats sherpa.toml)
sherpa scan <repo> --as-of 2026-03-01   # fix the window end (reproducing old states)
sherpa scan <repo> --top 50             # more hotspots
```

Exit 0 ok, 1 error (no repo, no origin, unknown trunk, invalid date). Summary on stderr, the model only in the
file or on stdout — so `--out -` is pipe-friendly.

Configuration in `<repo>/sherpa.toml` (optional, TOML because of stdlib `tomllib`):

```toml
[scan]
trunk = "dev"                          # ADR-0003 override
hotspots = 20
generated = ["gen/**"]                 # own generator family "custom"; extends sherpa.config.GENERATED_DEFAULT
```

## What is measured

| Field | Meaning | Source |
|---|---|---|
| `git.trunk` | `origin/<branch>`, how it was determined (`override` / `origin/HEAD` / `candidate`), SHA | ADR-0003 |
| `git.windows` | `as_of` = committer date of the trunk rev (or `--as-of`); `since_90d`, `since_30d` | — |
| `git.commits_*` | `total` incl. merges over the whole history; `90d`/`30d` non-merge commits in the window only | `git rev-list`, `git log --no-merges --since` |
| `git.files[]` | every file in the trunk tree: `loc` (null = binary), `generated`, commits/authors in the window, `last_change` | `git ls-tree`, `git cat-file --batch` |
| `git.dirs[]` | depth 1 + 2 (`""` = root): files, LOC sum, generator outputs, commits and authors touching something below (once per commit) | aggregate |
| `git.hotspots[]` | top N by `commits_90d × loc`, text only, non-generated only | Tornhill |
| `modules[]` | one module per manifest: `id`, `path`, `kind`, files/LOC/test files/generator outputs, `deps`/`dependents`/`tested_by` (in-repo only), churn per module, up to 3 hotspots | manifest parsers (T1) |
| `modules[].sub_dirs[]` | directories inside the module, depths 1–4 below its path: files, files in the module's language (`source_files`), Python package flag, LOC, commits and authors — the raw material for sub-units of single-manifest repositories | ADR-0020 |
| `modules[].coupling[]` | temporal coupling: up to 3 partner modules that changed in the same commits, with the shared count and the share of this module's commits; floors 5 shared and 30 %, commits touching more than `coupling.cap` modules excluded | Tornhill, ADR-0021 |
| `coupling` | how coupling was measured: `cap` = max(5, ⌈modules/2⌉), `skipped_commits` above the cap (squash merges, mass renames), `measured_commits`, the floors, `excluded` = the root module left out as a catch-all when other modules exist (ADR-0026), else `null` | ADR-0021, ADR-0026 |
| `generators[]` | one entry per (generator family, owning module): `home`, generated files/LOC, up to 5 sources and configs (closest to `home` first), regeneration command, `skill` | `scan/generators.py` |
| `conventions` | languages by LOC, CI files, container files | file tree |

### T1 — which manifests, how dependencies are resolved

| `kind` | Manifest | Module name | In-repo deps via | Test detection |
|---|---|---|---|---|
| `dotnet` | `*.csproj` `*.fsproj` `*.vbproj` | file stem | `<ProjectReference Include>` → manifest path (backslashes normalised, fallback file stem) | own test project: `IsTestProject`, package xunit/nunit/mstest/tunit, name `*Tests`/`*Test` → `is_test`, appears as `tested_by` on the referenced modules |
| `python` | `pyproject.toml` `setup.py` | `[project].name` / `[tool.poetry].name` | names from `dependencies`, `optional-dependencies`, Poetry groups, PEP 503 normalised (`Shop_Lib` ≙ `shop-lib`) | test directory in the module path, test files in the module |
| `node` | `package.json` | `name` | keys of `dependencies`/`devDependencies`/`peerDependencies` | test directory in the module path, test files in the module |
| `go` | `go.mod` | `module` | `require` lines and `replace` targets, exact module path | `*_test.go` |
| `rust` | `Cargo.toml` with `[package]` (a pure `[workspace]` is not a module) | `package.name` | `path = "…"` deps → manifest path; else name | test files in the module |
| `java` | `pom.xml` `build.gradle(.kts)` | `<artifactId>` (Gradle: directory name) | `<dependency><artifactId>` against other modules | `*Test.java`, `src/test/` |

Manifests under `node_modules/`, `vendor/`, `target/`, `bin/`, `obj/`, `dist/`, `build/`, `.venv/`, `packages/`
are not modules. Two manifests in the same directory (e.g. `package.json` next to `pyproject.toml`): the kind
with more source files under the directory wins (ADR-0025 — the ecosystem of the files, not of the alphabet; a
Python service with a `package.json` for its front-end tooling is `python`); a tie falls back to the manifest name.

External packages (`requests`, `serde`, `react`) do **not** appear in `deps`: for owner boundaries only what lives
in the repo counts. Test files = path contains `tests/`, `test/`, `__tests__/`, `spec/` or the name matches
`test_*.py`, `*_test.go`, `*.test.ts`, `*.spec.js`, `*Test.java`, `*Tests.cs`, `*_test.rs`, ….

### Generator families — generated code is regenerated, not explained (ADR-0011)

A family = globs for output, sources and configuration plus a regeneration command (`FAMILIES` in
`generators.py`): EF Core, Django and Alembic migrations, protobuf/gRPC, OpenAPI clients, GraphQL codegen, ResX,
.NET codegen (T4, source generators), `go generate`, Java codegen, test snapshots, frontend bundles, generic
patterns (`*.generated.*`, `generated/`), lockfiles (no skill) and `custom` from `sherpa.toml`. A path belongs to
the first matching family; output patterns take precedence over sources and configs. `home` is the common
directory of the outputs — the central place for a skill. Example: `ef-migrations` in `src/Shop.Migrations` with
399 files, source `ShopDbContext.cs`, command `dotnet ef migrations add`.

## Decisions and why

1. **Everything from the trunk rev, nothing from the working tree.** Untracked/local changes and the checked-out
   branch do not influence the model (`test_scan_ignores_local_branch_and_worktree`).
2. **`as_of` = committer date of the trunk rev.** The scan is byte-identical for the same rev, even weeks later.
   `--as-of` only for looking back.
3. **Committer date everywhere**, because `git --since` filters by it; the author date would mislead after rebases.
4. **Merges do not count in the windows.** A merge touches every file of the branch and would double the churn.
5. **Files deleted within the window are absent from the model.** Owner candidates are only files that still exist.
6. **Generated files are never hotspots.** On a 15k-file monorepo the top-5 hotspots of the first run were
   `*.Designer.cs`, `*ModelSnapshot.cs`, `*.resx` — tool noise. With the default globs, test infrastructure and
   business code lead the list. The files stay in `files`/`dirs` so `dirs.commits_*` stays honest.
7. **One process per kind of git call**, no loop over files (`cat-file --batch`, one `git log`). Runtime is git
   I/O; the flip criterion for a Rust core is in ADR-0001.
8. **Every file belongs to the deepest module** (the longest manifest path that is a prefix). A root manifest
   catches the rest. Files without a module (`docs/`, `.github/`, `Dockerfile`) count in `git.dirs` but in no module.
9. **Module churn counts once per commit.** A commit touching 40 files of a module is one commit — otherwise
   refactorings win every ranking. File churn (`git.files`) stays alongside.
10. **Language adapters (T2) are optional.** T1 reads manifests, not code. A 15k-file .NET/Node monorepo yields
    ~50 modules with correct `tested_by` via `ProjectReference` in 2.6 s.
11. **Test modules in every language.** .NET via project property, test package or name; otherwise via a test
    directory in the module path (`tests/suite`). This makes `tested_by` work for Python/Node/Go as well.
12. **Change coupling excludes big commits** (ADR-0021). On a squash-merge trunk every commit is one PR that
    touches docs, tests and several modules — measured naively, everything is coupled to everything at 100 %.
    CodeScene and code-maat exclude large changesets for the same reason; sherpa's cap is max(5, half the
    modules), and the model records how many commits it skipped so the number stays honest. A root module next
    to other modules is left out as a partner (ADR-0026): it owns everything no other manifest claims — docs,
    tests, scripts — so "changes together with `<root>` 74 %" would only say "touches the rest"; the model
    names it in `coupling.excluded`.
13. **Glob classification in constant time per path** (`GlobSet`): exact names via dict, `*<suffix>` via
    `endswith`, the rest via anchored regex, path globs only when their literal occurs. A naive regex alternation
    cost 0.8 s on 15k paths, `GlobSet` 0.05 s — the scan is not slower with generators than without (2.75 s).

## Interpretation for `plan`

Implemented in M2, rules in [`docs/concepts/harness-plan.md`](harness-plan.md): modules and uncovered directories are
units; `commits_90d`/`commits_30d`/`authors_90d`/`files` against rank and floor; `generated_files` decides skill
instead of agent; test modules against the most active business unit. `hotspots` and `tested_by` become owner-doc
sections and eval questions (M3/M4).
