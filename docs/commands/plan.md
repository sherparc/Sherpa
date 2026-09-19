# `sherpa plan`

Turn the codebase model into a harness plan: which owner docs, agents, librarians, skills and test-infra docs the
repository should get, each with its evidence — and which it should **not** get, each with the criterion that
would flip the no. Nothing is created; the plan is a YAML file you review and decide on.

## Synopsis

```
sherpa plan [REPO] [--rescan] [--no-fetch] [--out PATH | --out -] [--accept ADDRESS]... [--reject ADDRESS]...
```

Reads `REPO/.sherpa/codebase-model.json`, writes `REPO/.sherpa/harness-plan.yaml`, prints the console view.

## What it does

1. Loads the model. When it is missing, has an old schema, or the trunk moved since the scan (`git fetch origin`
   first unless `--no-fetch`), it runs [`sherpa scan`](scan.md) itself and writes the model.
2. Builds the **units**: every module plus every depth-1 directory no module covers (≥ 10 files, not a dot
   directory). A repository with a single root module — one `pyproject.toml` or `package.json` at the top, the
   most common shape — gets **sub-units** by the depth rule (ADR-0020): the first depth below the module at which
   at least two directories are source directories (≥ 2 files in the module's language; a package with
   `__init__.py` for Python; test and dot directories excluded). The root module keeps the repository-level owner
   doc; sub-units are directory units with their own facts. `[plan] units = ["src/app/*"]` in `sherpa.toml`
   replaces the rule, an empty list switches sub-units off; the note in the console says which applied.
3. Ranks the business units (non-test, not generator-dominated) by commits/90d and commits/30d.
4. Applies the stage-1 rules — rank **and** floor per building block (table below) — and produces one entry per
   (kind, target) with `evidence` (model fields only), `checks` (✓/✗ per criterion), `cost` and, for a no,
   `reason` with the flip criterion.
5. Carries `decision:` values over from the previous `harness-plan.yaml` (matched by kind, target, scope), then
   applies `--accept`/`--reject` given on the command line.
6. Writes the YAML (fixed field order, validated against the schema) and prints the console view.

The rules, the reasoning and the calibration behind them: [concepts/harness-plan.md](../concepts/harness-plan.md).

## Rules at a glance

| Kind | Proposed when | Reasoned no when |
|---|---|---|
| `outcome` | always — a harness without an outcome signal is not created (ADR-0008) | never |
| `owner-doc` | the unit has ≥ 1 commit/90d **or** ≥ 1 dependent, **and** ≥ `owner_doc_min_files` files **or** ≥ 1 dependent | dormant (0 commits/90d, 0 dependents) or small (< 5 files, 0 dependents) — listed, with the flip criterion, and counted in a note |
| `agent` | rank ≤ ⌈n · `agent_top`⌉ by commits/90d **and** ≥ 20 commits/90d, ≥ 30 files, ≥ 2 authors/90d | within reach (rank or commit floor met) but a floor missing — listed; everything else counted in a note |
| `librarian` | top `librarian_top_n` by commits/30d **and** (≥ 30 commits/30d or ≥ 80 commits/90d) | within reach but below both floors — listed |
| `test-infra` | the most active test unit has ≥ as many commits/90d as the most active business unit | otherwise listed with the comparison |
| `skill` | a generator family with ≥ 5 generated files (config alone counts only for families without detectable output, e.g. OpenAPI clients) | below the floor — counted in a note |

A unit whose files are ≥ 50 % generator output gets no agent, no librarian and no rank; the generator's skill
takes over (ADR-0011: generated code is regenerated, not explained). All thresholds are configurable
([reference/configuration.md](../reference/configuration.md)).

## Options

| Option | Default | Effect |
|---|---|---|
| `REPO` | `.` | repository root |
| `--rescan` | reuse the model when current | rebuild the model even if it exists and the trunk did not move |
| `--no-fetch` | fetch | no `git fetch origin` before checking whether the trunk moved or scanning |
| `--out PATH` | `REPO/.sherpa/harness-plan.yaml` | write the plan elsewhere; decisions are read from that file too |
| `--out -` | — | YAML to stdout, console view to stderr |
| `--accept ADDRESS` | — | set `decision: accept` on one entry; repeatable. `ADDRESS` is `kind:target` or `kind:target:scope` (`agent:pay`, `owner-doc:web:svc/web`) — the same address the state and `status` use |
| `--reject ADDRESS` | — | set `decision: reject`; repeatable. An unknown address is an error that lists the entries of that kind (five at most, `(+N more)`); an address without a kind, or with a kind the plan does not have, names the kinds in the plan; a short address that matches two scopes is an error that asks for the scope |

## Output

Console view (stdout), one line per entry: `+` proposal, `-` reasoned no, then the notes. A `[accept]` or
`[reject]` suffix marks an entry with a decision.

```console
$ sherpa plan .
harness-plan.yaml — 6 proposals, 4 reasoned no's
  + outcome     shop                          mandatory: no harness without an outcome signal (ADR-0008) ✓
  + owner-doc   pay                           24 commits/90d, 1 dependents ✓ · 40 files ✓
  + owner-doc   core                          1 commits/90d, 2 dependents ✓ · 3 files ✓
  + agent       pay                           rank 1/4 churn ✓ · 24 commits/90d ✓ · 40 files ✓ · 2 authors ✓
  + test-infra  suite                         26 commits/90d vs. 24 (pay) ✓
  + skill       regenerate-django-migrations  svc/pay/pay/migrations · 6 generated files, 1 configs ✓
  - owner-doc   web                           1 commits/90d, 0 dependents ✓ · 3 files ✗
  - owner-doc   old                           0 commits/90d, 0 dependents ✗ · 2 files ✗
  - librarian   pay                           rank 1/4 momentum ✓ · 24 commits/30d, 24/90d ✗
  - librarian   core                          rank 2/4 momentum ✓ · 1 commits/30d, 1/90d ✗
  1 dormant units without owner doc (0 commits/90d, 0 dependents): old — the first commit turns them into a proposal; each is listed above as a no.
  1 small units without owner doc (< 5 files, 0 dependents): web — listed above as no's; owner_doc_min_files in sherpa.toml [plan] moves the floor, a dependent overrides it.
  not listed, out of reach: 2 units for agent (rank > 1 and < 20 commits/90d), 1 for librarian (rank > 2 and below both floors).
→ .sherpa/harness-plan.yaml (2 decisions kept)
```

The file (`.sherpa/harness-plan.yaml`): a four-line comment header, then `sherpa`, `schema_version`, `repo`,
`model` (trunk, rev, as_of), `thresholds` (the values used), `ranking` (units by commits/90d and /30d), `notes`
and `entries`. One entry:

```yaml
- kind: librarian
  target: pay
  scope: svc/pay
  default: skip
  decision: null
  evidence: {path: svc/pay, files: 40, generated_files: 6, commits_90d: 24, commits_30d: 24, authors_90d: 2, dependents: 1,
    rank_commits_30d: 1/4}
  checks:
  - rank 1/4 momentum (top 2 by commits/30d) ✓
  - 24 commits/30d, 24/90d (commits/30d ≥ 30 or commits/90d ≥ 80) ✗
  cost: 1 scheduled task, 1 SKILL file, anchor upkeep per run
  reason: '24 commits/30d, 24/90d. Flips when: commits/30d ≥ 30 or commits/90d ≥ 80'
```

Every number is a model field, every check names the measurement and the criterion. Field semantics:
[`harness-plan.schema.json`](../../src/sherpa/schemas/harness-plan.schema.json).

## Deciding

Edit `decision:` per entry — `accept`, `reject` or `null`. [`sherpa apply`](apply.md) applies every `propose`
that is not rejected and every `skip` that is accepted. Decisions survive re-plans: the console tail says how many
were kept (`(2 decisions kept)`). An entry that disappears from the plan (a module was deleted) takes its decision
with it, and the console says so once, under the entries: `agent:pay:svc/pay [reject] is no longer in the plan —
dropped`. A unit whose manifest name changes and whose path stays keeps its decision — the one decided entry of
that kind and scope left, the one new entry of that kind and scope arrived — and the console says that once too:
`agent:billing:svc/pay [reject] — followed from agent:pay:svc/pay (same path, renamed)`; two candidates on either
side carry nothing and are named as dropped. An entry that changes kind or scope is a new entry.

For scripts and CI the same decision is a flag: `sherpa plan --accept librarian:pay --reject agent:pay` writes
exactly the `decision:` values a hand would, and the tail counts them (`(2 decided now)`); the next plan keeps
them like any other decision. Addresses are `kind:target[:scope]` — `sherpa plan` prints them as the first two
columns, `status` and the state use the same string.

`covered:` is the path of an existing file that already fills the entry (an agent or owner doc of that unit).
Three sources, one precedence: what you write by hand — `covered: .claude/docs/modules/kes.md` on the
`owner-doc` entry of a unit whose doc adopt could not match by name or mentions (ADR-0046); the unit's own
nested `AGENTS.md`, which `plan` itself sets on the entry when the file has prose of its own (ADR-0049); and
what [`sherpa adopt`](adopt.md) links in the state. A hand-set cover is kept across re-plans like a decision and wins over the state; a cover
whose file is gone is dropped with a note (`owner-doc:kes:src/Kes was covered by …, which no longer exists —
dropped`). A covered proposal is shown as `[covered by <path>]` and `apply` renders nothing for it; `decision:
accept` overrides that when you want sherpa's version next to yours. The console tail counts them (`(2 covered
by existing files)`).

## Configuration

`[plan]` in `REPO/sherpa.toml` — every threshold, with defaults, in
[reference/configuration.md](../reference/configuration.md). Unknown keys are an error, so a typo cannot silently
fall back to a default.

## Exit codes and errors

| Exit | When | Message |
|---|---|---|
| 0 | plan written | console view, `→ <path>` |
| 1 | scan failed (no repository, no origin, no trunk) | as for [`sherpa scan`](scan.md#exit-codes-and-errors), prefixed `sherpa plan:` |
| 1 | `sherpa.toml [plan]` has unknown keys | `sherpa plan: sherpa.toml [plan]: unknown keys ['agent_top_n']; allowed: [...]` |
| 1 | previous plan has an invalid decision | `sherpa plan: harness-plan.yaml: decision 'yes' at agent pay — allowed: ('accept', 'reject')` |
| 0 | `.sherpa/state.json` torn or foreign — `covered:` marks are dropped, `… `sherpa adopt` rebuilds it …` on stderr (ADR-0034) | console view, `→ <path>` |
| 1 | previous plan does not match the schema | `sherpa plan: harness-plan.yaml invalid at entries/3/kind: 'foo' is not one of [...]` |
| 1 | `--accept`/`--reject` names no entry, or two | `sherpa plan: --accept agent:Nope: no such entry — entries of that kind: agent:pay:svc/pay` · `… ambiguous — owner-doc:x:a/x, owner-doc:x:b/x; give the scope` |

Informational lines on stderr: `sherpa plan: model scanned → …`, `sherpa plan: origin/main moved since the last
scan — rescanning`, `sherpa plan: rebuilding the model (model has schema_version 3, expected 4)`.

## Determinism and performance

Same model and configuration → byte-identical YAML (no clock, no LLM; `test_plan_is_deterministic`). With an
existing model the plan for a 15k-file monorepo with ~50 modules takes 0.16 s; the scan it may trigger 2.7 s.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| A module I care about has no agent | rank or a floor not met — the line says which | lower `agent_min_*` or `agent_top` in `[plan]`, or `decision: accept` on the no |
| "not listed, out of reach: 12 units for agent" | units that meet neither the rank nor the commit floor are counted, not listed — the flip criterion there is not information | none needed; raise `agent_top` to see more of them |
| A directory like `infrastructure/` gets nothing | fewer than `dir_min_files` files, or a module covers it | lower `dir_min_files` |
| A migrations project gets a skill instead of an agent | ≥ 50 % of its files are generator output | intended (ADR-0011); the skill names sources, config and command |
| My decisions vanished | the entry's key changed (kind, target, scope) — e.g. a module was renamed | set the decision again on the new entry (`--accept kind:target`) |
| My single-package repo shows sub-units I do not want (or the wrong ones) | the depth rule picked the first depth with two source directories | `[plan] units = [...]` in `sherpa.toml` names them; `units = []` switches them off |
| `harness-plan.yaml invalid at …` | hand edit broke the schema (a check line without ✓/✗, a wrong kind) | fix the line or delete the file and re-plan (decisions are lost then) |

## See also

[`sherpa scan`](scan.md) · [`sherpa apply`](apply.md) · [concepts/harness-plan.md](../concepts/harness-plan.md) ·
ADR-0005 (YAML, check-in), ADR-0006 (rank and floor), ADR-0011, ADR-0012 (units, reach, decisions), ADR-0020 (sub-units).
