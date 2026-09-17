# `sherpa scan`

Capture a repository as a deterministic model: modules, dependencies, churn, hotspots, generator families —
measured on `origin/<trunk>`, without an LLM, byte-identical for the same commit.

## Synopsis

```
sherpa scan [REPO] [--trunk BRANCH] [--no-fetch] [--as-of DATE] [--top N] [--out PATH | --out -]
```

`REPO` is the repository root (default: the current directory). The result is written to
`REPO/.sherpa/codebase-model.json`; a one-line summary goes to stderr.

## What it does

1. `git fetch origin` (skipped with `--no-fetch`) — the only network access Sherpa ever makes.
2. Resolves the trunk as `origin/<branch>`: `--trunk`, else `[scan].trunk` in `sherpa.toml`, else `origin/HEAD`,
   else the first existing of `main`, `master`, `dev`, `develop`, `trunk`.
3. Reads the trunk tree (`git ls-tree`, `git cat-file --batch`) — never the working tree or the checked-out
   branch — and the commit history for two windows: 90 and 30 days ending at the trunk's committer date.
4. Finds modules from manifests (.NET, Python, Node, Go, Rust, Java), in-repo dependencies in both directions,
   test modules and `tested_by`.
5. Classifies generator families by path (migrations, protobuf, OpenAPI, codegen, snapshots, bundles, lockfiles,
   your own globs) and excludes generated files from hotspots.
6. Writes the model (schema v5, sorted keys) and validates it against the JSON schema (stdlib validator,
   ADR-0036).

Rules and the reasoning behind every measurement: [concepts/scan.md](../concepts/scan.md).

## Options

| Option | Default | Effect |
|---|---|---|
| `REPO` | `.` | repository root; must be a git repository with a remote `origin` |
| `--trunk BRANCH` | from `sherpa.toml`, else detected | force the trunk; `dev` and `origin/dev` are both accepted. Beats the config file. |
| `--no-fetch` | fetch | skip `git fetch origin` — offline work, CI with a fresh clone, tests. The model is then only as current as the local `origin/*` refs. |
| `--as-of DATE` | committer date of the trunk rev | end of the 90-/30-day windows: `YYYY-MM-DD` or ISO-8601. Use it to reproduce an older state; the rev itself is not moved. |
| `--top N` | 20, or `[scan].hotspots` | number of hotspots in `git.hotspots` |
| `--out PATH` | `REPO/.sherpa/codebase-model.json` | write the model elsewhere |
| `--out -` | — | model to stdout, summary to stderr — pipe-friendly (`sherpa scan --out - \| jq .modules`) |

## Output

Summary line (stderr):

```console
$ sherpa scan .
sherpa scan: shop @ origin/main 5db69c4ddd (origin/HEAD) — 50 files, 52 commits/90d, 52/30d, 20 hotspots, 5 modules → /path/shop/.sherpa/codebase-model.json
```

The model (`.sherpa/codebase-model.json`), top level:

| Key | Content |
|---|---|
| `sherpa`, `schema_version` | version that wrote the file; schema `3` |
| `repo`, `origin` | directory name; URL of `origin` |
| `git.trunk` | `ref` (`origin/main`), `source` (`override` / `origin/HEAD` / `candidate`), `rev` |
| `git.windows` | `as_of`, `since_90d`, `since_30d` (ISO-8601 UTC) |
| `git.commits_total`, `commits_90d`, `commits_30d`, `authors_90d`, `first_commit`, `last_commit` | repo-wide history figures; the windows count non-merge commits only |
| `git.files[]` | every file in the trunk tree: `path`, `loc` (`null` = binary), `generated`, `commits_90d`, `commits_30d`, `authors_90d`, `last_change` |
| `git.dirs[]` | directories at depth 1 and 2 (`""` = root): `files`, `loc`, `generated_files`, commits and authors touching anything below |
| `git.hotspots[]` | top N by `commits_90d × loc`, hand-written text files only |
| `modules[]` | one per manifest — see below |
| `generators[]` | one per (family, owning module) — see below |
| `conventions` | `languages` (LOC per language, descending), `ci` files, `containers` files |

A module, exactly as written:

```json
{
  "id": "pay", "path": "svc/pay", "kind": "python", "manifest": "svc/pay/pyproject.toml", "is_test": false,
  "files": 40, "loc": 42, "test_files": 0, "generated_files": 6,
  "deps": ["core"], "dependents": ["suite"], "tested_by": ["suite"],
  "commits_90d": 24, "commits_30d": 24, "authors_90d": 2,
  "hotspots": ["svc/pay/pay/mod00.py", "svc/pay/pay/mod01.py", "svc/pay/pay/mod02.py"]
}
```

A generator:

```json
{
  "family": "django-migrations", "title": "Django Migrations", "module": "pay", "home": "svc/pay/pay/migrations",
  "generated_files": 6, "generated_loc": 6,
  "sources": ["svc/pay/pay/models.py"], "configs": ["svc/pay/manage.py"],
  "command": "python manage.py makemigrations", "skill": true
}
```

Field semantics are owned by the schema:
[`codebase-model.schema.json`](../../src/sherpa/schemas/codebase-model.schema.json).

## Configuration

`REPO/sherpa.toml`, section `[scan]` — full reference in [reference/configuration.md](../reference/configuration.md):

```toml
[scan]
trunk = "dev"                 # override the trunk detection (ADR-0003)
hotspots = 20                 # size of git.hotspots
generated = ["gen/**"]        # your own generator family "custom": excluded from hotspots, proposed as a skill
```

## Exit codes and errors

| Exit | When | Message (stderr) |
|---|---|---|
| 0 | model written | summary line |
| 1 | not a repository | `sherpa scan: /path is not a git repository` |
| 1 | no `origin` | `sherpa scan: /path has no remote 'origin' — sherpa only scans against origin` |
| 1 | `--trunk` or `[scan].trunk` does not exist | `sherpa scan: trunk override 'x' does not exist as origin/x` |
| 1 | no trunk found | `sherpa scan: no trunk found: origin/HEAD is not set and none of ('main', 'master', 'dev', 'develop', 'trunk') exists on origin. Fix: 'git remote set-head origin -a' or 'trunk' in sherpa.toml` |
| 1 | bad `--as-of` | `sherpa scan: …` with the parse error |
| 1 | `sherpa.toml` invalid | `sherpa scan: sherpa.toml [plan]: unknown keys […]; allowed: […]` |

## Determinism and performance

- Same `origin/<trunk>` rev → byte-identical model, also weeks later (`as_of` is the trunk's committer date,
  not the clock). Tested in `test_scan_is_deterministic`.
- Local branches, uncommitted changes and untracked files never influence the model.
- One git process per kind of call, no loop over files. A 15k-file monorepo with ~50 modules scans in about
  2.7 s; generator classification adds 30 ms.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `no trunk found` on a fresh clone | `origin/HEAD` not set and the default branch has an unusual name | `git remote set-head origin -a`, or `--trunk <branch>` / `[scan].trunk` |
| Hotspots are all `*.Designer.cs`, `*.resx`, snapshots | a generator Sherpa does not know | add the globs to `[scan].generated` — they leave the hotspots and become a skill candidate |
| A module is missing | its manifest lives under `node_modules/`, `vendor/`, `dist/`, `build/`, `target/`, `bin/`, `obj/`, `.venv/`, `packages/` — those are never modules | move the manifest or accept it: files still count in `git.dirs` |
| Two manifests in one directory | the alphabetically first wins (`Cargo.toml` before `package.json`) | split the directory; open question 4 in [plan.md](../plan.md) |
| Scan shows fewer commits than `git log` | merges do not count in the windows; the windows end at the trunk's committer date, not today | `commits_total` has the full history |
| Scan behind the remote | `--no-fetch`, or no fetch because of an offline machine | run without `--no-fetch` |

## See also

[`sherpa plan`](plan.md) reads this model · [concepts/scan.md](../concepts/scan.md) owns the measurement rules ·
ADR-0003 (trunk detection), ADR-0011 (generator families).
