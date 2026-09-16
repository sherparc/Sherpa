# Configuration — `sherpa.toml`

Optional file at the repository root. TOML, because Python's `tomllib` reads it without a dependency. Unknown
keys in `[plan]` are an error — a typo never falls back silently to a default. Command-line options beat the
file (`--trunk`, `--top`).

```toml
[scan]
trunk = "dev"                 # trunk override; "dev" and "origin/dev" both work
hotspots = 20                 # size of git.hotspots
generated = ["gen/**"]        # your own generator family "custom" (globs)

[plan]
agent_top = 0.25              # agent: top quartile by commits/90d …
agent_min_commits_90d = 20    # … and these floors
agent_min_files = 30
agent_min_authors_90d = 2
librarian_top_n = 2           # librarian: top 2 by commits/30d …
librarian_min_commits_30d = 30   # … and one of these floors
librarian_min_commits_90d = 80
dir_min_files = 10            # a directory without a module counts as a unit from this many files
generated_share = 0.5         # from this share of generator output: no agent/librarian, a skill instead
skill_min_generated_files = 5 # skill proposal from this many generated files
owner_doc_min_files = 5       # owner doc from this many files — a dependent overrides the floor
```

## `[scan]`

| Key | Type | Default | Effect |
|---|---|---|---|
| `trunk` | string | detected (ADR-0003: `origin/HEAD`, then `main`, `master`, `dev`, `develop`, `trunk`) | measure this branch on `origin`. Must exist as `origin/<trunk>`, otherwise `scan` fails with `trunk override 'x' does not exist as origin/x`. |
| `hotspots` | int | `20` | number of entries in `git.hotspots` (top by `commits_90d × loc`, hand-written files only) |
| `generated` | list of globs | `[]` | extra generator family **`custom`**. Matching files are excluded from hotspots, counted as generator output per module and directory, and proposed as a skill `regenerate-custom` when ≥ `skill_min_generated_files`. Globs without `/` match the file name (`*.g.cs`), globs with `/` match the path (`gen/**`); `*` also matches `/`. The built-in families (migrations, protobuf, OpenAPI, GraphQL codegen, ResX, .NET codegen, `go generate`, Java codegen, snapshots, bundles, lockfiles) stay active. |

## `[plan]`

Thresholds are **rank and floor** (ADR-0006): a relative criterion so a five-person repo and a fifty-module
monorepo both get a sensible number of proposals, plus an absolute floor so a tiny repo does not get an agent for
three commits.

| Key | Type | Default | Used by | Meaning |
|---|---|---|---|---|
| `agent_top` | float 0–1 | `0.25` | agent | rank ≤ ⌈n · agent_top⌉ by commits/90d among the rankable business units (`rank 1/4 churn`) |
| `agent_min_commits_90d` | int | `20` | agent | floor on commits in the 90-day window |
| `agent_min_files` | int | `30` | agent | floor on files in the unit |
| `agent_min_authors_90d` | int | `2` | agent | floor on distinct authors in the 90-day window — one person's module needs no agent |
| `librarian_top_n` | int | `2` | librarian | top N by commits/30d (`rank 1/4 momentum`) |
| `librarian_min_commits_30d` | int | `30` | librarian | floor, alternative 1 |
| `librarian_min_commits_90d` | int | `80` | librarian | floor, alternative 2 — one of the two must hold |
| `dir_min_files` | int | `10` | units | a depth-1 directory no module covers becomes a unit from this many files (dot directories never) |
| `generated_share` | float 0–1 | `0.5` | units | a unit with this share of generator output is generator-dominated: no agent, no librarian, no rank; its generator's skill takes over (ADR-0011) |
| `skill_min_generated_files` | int | `5` | skill | a generator family is proposed as a skill from this many generated files; configuration files alone count only for families without detectable output (OpenAPI clients) |
| `owner_doc_min_files` | int | `5` | owner-doc | a unit with fewer files and **no dependents** gets no owner doc (listed as a no, counted in a note): a two-file tool is explained where it is used, and a doc nobody links to is the first to go stale. Any dependent overrides the floor. |

Every threshold in effect is written into `harness-plan.yaml` under `thresholds`, so a plan is readable without
the config file. The owner-doc activity rule (≥ 1 commit/90d or ≥ 1 dependent), the test-infra comparison (most active
test unit vs. most active business unit) and the "within reach" listing rule are not configurable — they define
what a plan is (ADR-0012).

## Errors

| Message | Cause |
|---|---|
| `sherpa.toml [plan]: unknown keys ['agent_top_n']; allowed: ['agent_min_authors_90d', …]` | a key that does not exist — check the spelling |
| `trunk override 'x' does not exist as origin/x` | `[scan].trunk` names a branch that is not on `origin` (fetch first?) |
| TOML parse error | invalid TOML; the message names the line |

## Where the values come from

The defaults were calibrated on fixture repositories of five to thirteen modules and on a large monorepo
(~50 modules, ~15k files): with them a five-module repo gets one agent, a fifty-module repo a dozen at most (the quartile) and fewer
where the floors bite, two librarians, one test-infra doc. Calibration notes and the reasoning per rule:
[concepts/harness-plan.md](../concepts/harness-plan.md).
