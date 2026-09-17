# Sherpa — Plan

> **Created:** 2026-09-16 · **Revised:** 2026-09-17 (revision 15: two findings from a first run on a large repository with two homes, F18/F19 — a preview never refuses (assumes `.agents` and says so, ADR-0036) and a target directory that is a repository of its own is named (ADR-0037); revision 14: F17 closed — `self-update` saves the wheel under its PEP 427 name and finds the tag with `git ls-remote` without a token, verified with pip itself, ADR-0035; revision 13: the review's F16 closed — `adopt` no longer refuses a stale plan and `plan`/`status`/`adopt` run on a torn state, ADR-0034, so a broken index plus a moved trunk has a way out; revision 12: an external review of v0.7.0 found the write path overwriting a file that moved between the preview and the confirmation — writing through symlinks, a torn harness after a write error, and `adopt` lifting the hand-edit guard on base files — closed as M3f with compare-and-swap, a symlink guard, atomic writes with rollback and base files as yours, ADR-0030 to 0033, §10.4) · **Author:** Claude (Opus 5) with Andrei
> **Status:** v0.7.4 — M0, M1, M1a, M2, M2b, M3a, M3t, M3c, M3d, M3e, M3f done; order from here: M3h → M5 → M7a → M6-lite → M4 → M6 → M3b → M7 (§7.3, §9, §10)
> **Origin of the patterns:** production Claude Code harnesses built and analysed in practice (owner docs, agents with
> knowledge manifests, librarians, deterministic checkers) plus the industry patterns in §2. Sherpa is a generic
> product; no customer project is named anywhere in this repo.

## 0. Goal in one sentence

Sherpa stands **above** one or more repos, ingests the codebase deterministically, proposes a harness
infrastructure (owner docs, agents, skills, commands, librarians, evals, outcome channel) **with evidence and
cost**, and after approval creates exactly that — idempotently, with state, without overwriting manual work.

**Direction beyond the milestone table (2026-09-17, reordered with ADR-0023):** independence from any single
agent runtime — reached in this order. First through the **open runtimes**: Hermes Agent reads the nested
`AGENTS.md` chain and `.agents/skills` Sherpa already writes, so a thin `hermes` target (M3h) puts the harness in
front of its users with a day of work; Codex, Cursor and Copilot follow as adapters when a corpus repository uses
them, and Sherpa itself is installed **inside** those runtimes as a thin plugin or bundle (M7a, ADR-0024) — one
command where the user already works. Second, the **provider layer** (M6-lite, ADR-0004: thin, framework-free — bring your own key, local models
through OpenAI-compatible servers, Anthropic, OpenAI, Chinese providers) for evals and enrichment. Last, and only
if the evals and librarians need it, an **executor of Sherpa's own** for those two jobs — never a chat runtime
that competes with Claude Code or Hermes (§9). Every design choice keeps that door open: runtime-neutral formats
where possible (owner docs, skills), runtime-specific parts (agent front matter, hooks, `CLAUDE.md`) isolated in
`apply/render.py`. The milestones below are executed in order first.

Noted for the runtime (2026-09-17, from an agent runtime's session-store recovery design): sessions get the
same split as the harness state (ADR-0017) — the transcript is canonical and append-only with a spool file when
the store is corrupt, search indexes are derived and rebuildable, one `repair` command with an automatic backup,
and derived structures detach without blocking live operation. Not built before the runtime is.

## 1. Non-goals (deliberate)

| Non-goal | Why |
|---|---|
| Create everything on day 1 | Bloat is the measured weakness of grown harnesses (fat agents, agents without manifests, dormant docs). The default is `skip`. |
| LLM prose as owner doc | Plausible-but-wrong docs = drift from day 0. Owner doc = skeleton + scanner facts; prose stays `unverified` until an eval or a human confirms it. |
| An agent runtime of its own **in v1** | v1 produces artefacts for an agent runtime, it does not run agents. Target runtime v1: Claude Code (`.claude/`); a repo with `AGENTS.md` keeps it as the source (`CLAUDE.md` imports it). The runtime itself is the direction in §0 — after the milestone table, not before. |
| Web app first | The CLI is testable, CI-capable and callable by Claude Code itself. Web = a later viewer. |
| The template harness as the test case | It is the template. The proof must succeed on **foreign** repos. |
| Language parsers as a requirement | T0+T1 (git + manifests) suffice for owners, churn, evals. Language adapters (T2) are plugins. |

## 2. Architecture — eight commands, three artefacts

```
sherpa doctor ──► ✓/!/✗ per prerequisite (Python, git, origin, trunk, config, runtime, install, update) with a fix   — first contact
sherpa scan   ──► .sherpa/codebase-model.json   deterministic, 0 LLM     (T0 git · T1 manifests · generator families · T2 adapters optional)
sherpa adopt  ──► .sherpa/state.json            take an existing harness into the state, change nothing; rebuild a lost state (§2.6)
sherpa plan   ──► .sherpa/harness-plan.yaml     deterministic rules, LLM enrichment optional (M6)
sherpa apply  ──► .claude/** + .sherpa/state.json   dry run first, then deterministic, idempotent, markers
sherpa status ──► diff state ↔ file system, eval regression, outcome labels per harness version
sherpa self-update ──► the latest GitHub release via the installer that owns this copy (uv, pipx, pip); daily hint
```

`.sherpa/` is Sherpa's working directory in the target repo. Configuration lives next to it in `sherpa.toml`
(TOML because of stdlib `tomllib`; fields in `src/sherpa/config.py`). `harness-plan.yaml` and `state.json` are
checked into the target repo, `codebase-model.json` is not (ADR-0005).

Industry patterns that demonstrably work:

| Pattern | What Sherpa takes from it |
|---|---|
| Terraform `plan`/`apply` + state | proposal before effect; re-run = diff, never overwrite; the state knows every generated file |
| Backstage catalog + scaffolder | an owner per component; templates with parameters |
| Tornhill hotspots (churn × size) | drift proxy on day 0 from `git log`, without sync history |
| Manifest/dependency graph | module boundaries = owner candidates; `tested_by` for free |
| `<auto-generated>` markers | generated vs. hand-edited distinguishable; hand-edited is never overwritten |
| Renovate/Dependabot | librarian = a small, scoped bot that proposes changes instead of editing directly |

### 2.1 Scanner → `codebase-model.json` — details in `docs/concepts/scan.md`

Deterministic, testable with fixture repos, **language-agnostic**. Three layers; each yields a valid model
without the next one:

| Layer | Source | Applies to | Yields |
|---|---|---|---|
| **T0 git** ✅ M1 | `git log`, `git ls-tree` against `origin/<trunk>` (ADR-0003) | every repo | churn, hotspots, authors, file tree, LOC, generated files |
| **T1 structure** ✅ M1a | manifests (`*.csproj`, `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`) | every repo with manifests | modules, in-repo deps, `tested_by`, churn per module, languages/CI/containers |
| **Generators** ✅ M2 | path patterns per family (migrations, protobuf, OpenAPI, codegen, snapshots, bundles, lockfiles, `custom`) | every repo | `generators[]` with `home`, sources, config, command; `generated_files` per module/directory (ADR-0011) |
| **T2 language** (M3b) | adapters (`sherpa/adapters/<lang>/`), optionally tree-sitter | per language, first: `dotnet`, `python` | symbols as code anchors, patterns for skill proposals |

A repo without an adapter gets T0+T1 and with that owner docs, hotspots, churn thresholds and evals from the
graph — only code anchors and skill evidence from code patterns are missing.

```json
{
  "sherpa": "0.3.0", "schema_version": 3, "repo": "…", "origin": "…",
  "git": {"trunk": {"ref": "origin/main", "source": "origin/HEAD", "rev": "…"}, "windows": {…},
          "commits_90d": 1018, "files": […], "dirs": […], "hotspots": […]},          ← T0 (M1)
  "modules": [                                                                         ← T1 (M1a)
    {"id": "Shop.Pricing", "path": "src/Shop.Pricing", "kind": "dotnet", "manifest": "…csproj",
     "is_test": false, "files": 212, "loc": 18400, "test_files": 0,
     "deps": ["Shop.Core"], "dependents": ["Shop.Api"], "tested_by": ["Shop.Pricing.Tests"],
     "commits_90d": 143, "commits_30d": 51, "authors_90d": 3, "generated_files": 0,
     "hotspots": ["src/Shop.Pricing/Services/PriceEngine.cs"]}
  ],
  "generators": [                                                                      ← M2 (ADR-0011)
    {"family": "ef-migrations", "module": "Shop.Migrations", "home": "src/Shop.Migrations", "generated_files": 399,
     "sources": ["src/Shop.Migrations/Context/ShopDbContext.cs"], "configs": [], "command": "dotnet ef migrations add <Name> --project <home>", "skill": true}
  ],
  "conventions": {"languages": {"csharp": 5953126, "typescript": 480000}, "ci": […], "containers": […]},
  "anchors": […]                                                                       ← T2 (M3b), planned
}
```

### 2.2 Planner → `harness-plan` — two stages

**Stage 1 (M2 ✅, deterministic):** rules over the model; the owner of the details is
[`docs/concepts/harness-plan.md`](concepts/harness-plan.md). Every entry has `evidence` (model fields only), `checks` (each
criterion with ✓/✗), `cost`, `default` and, for `skip`, a `reason` with a flip criterion. Thresholds are
**relative with an absolute floor** (ADR-0006); values in `sherpa.toml [plan]`.

| Building block | Scope | `propose` when | otherwise |
|---|---|---|---|
| Outcome channel | repo | always, **first** — the minimum comes with `apply` (M3a ✅), evaluation in M5 (§2.5) | — |
| Owner doc | per unit (module or depth-1 directory without a module, ADR-0012) | not dormant: ≥ 1 commit/90d or ≥ 1 dependent; not small: ≥ `owner_doc_min_files` (5) files or ≥ 1 dependent (ADR-0014) | visible `skip` ("dormant", "small unit"), count lines in `notes` |
| Agent | per business unit | top quartile by `commits_90d` **and** floors `commits_90d ≥ 20`, `files ≥ 30`, `authors_90d ≥ 2` | `skip` listed when within reach (rank or commit floor met) |
| Librarian | per business unit | top **2** by `commits_30d`, floor `commits_30d ≥ 30` **or** `commits_90d ≥ 80` | `skip` listed when within reach |
| Generator-dominated | unit with ≥ 50 % generator output | no agent/librarian, no rank; **skill** `regenerate-<family>` at the `home` (ADR-0011) | skill below the floor (5 files) as a count line |
| Test infra | most active test unit | commits/90d ≥ most active business unit (analysis practice: blind spot number one) | `skip` listed |
| Eval | per agent | automatically from the graph (§2.4, M4) | — |
| Skill from code patterns | per pattern | needs T2 (M3b): pattern found ≥ 2× in code | until then generator skills only |

Calibrated on a large monorepo (~50 modules, ~15k files): about 60 proposals, ~16 no's within reach, ~60 units
counted as out of reach; runtime with an existing model 0.16 s. Human decisions (`decision: accept | reject`)
survive another `plan` run (ADR-0012).

**Stage 2 (M6, optional, LLM):** enrichment of stage-1 entries — descriptions, merging related modules, skill
candidates from T2 patterns. The LLM may **comment on and add to** entries, never remove stage-1 entries or bypass
thresholds. Output is validated against the plan schema (ADR-0004); the plan header carries `model`,
`prompt_hash`. Without stage 2 the plan is fully usable.

```yaml
- kind: agent
  target: pay
  scope: svc/pay
  default: propose
  decision: null
  evidence: {path: svc/pay, files: 40, generated_files: 6, commits_90d: 24, commits_30d: 24, authors_90d: 2, dependents: 1, rank_commits_90d: 1/4}
  checks: [rank 1/4 churn · rank ≤ 1 by commits/90d ✓, 24 commits/90d · commits/90d ≥ 20 ✓, 40 files · files ≥ 30 ✓, 2 authors · authors/90d ≥ 2 ✓]
  cost: 1 agent with knowledge manifest, 1 eval catalogue from the graph
- kind: librarian
  target: pay
  scope: svc/pay
  default: skip
  decision: null
  evidence: {…, rank_commits_30d: 1/4}
  checks: [rank 1/4 momentum · top 2 by commits/30d ✓, '24 commits/30d, 24/90d · commits/30d ≥ 30 or commits/90d ≥ 80 ✗']
  cost: 1 scheduled task, 1 SKILL file, anchor upkeep per run
  reason: '24 commits/30d, 24/90d. Flips when: commits/30d ≥ 30 or commits/90d ≥ 80'
```

Approval: by editing the file (`decision:`), interactively (`sherpa apply` asks per entry without a decision,
M3) or in Claude Code via `/sherpa-plan` (M7). Format: YAML (ADR-0005).

### 2.3 Harnessing → `.claude/**` + `.sherpa/state.json` (M3a ✅, `docs/concepts/harness-apply.md`)

- Templates: the **generic part** of proven harnesses (ADR-0002): owner doc, agent with `knowledge:` manifest,
  librarian SKILL, generator skill, `CLAUDE.md` block, hook set, checker. Facts have one owner (the owner doc);
  agents carry role and manifest and say so; generated code points to its skill (ADR-0011).
- **Target layer (ADR-0015, M3t ✅):** one runtime-neutral core under `home` (`.agents/docs/modules`,
  `.agents/skills`, the checker copy; `.claude` for Claude-only repos; the CLI asks when both exist) and one
  adapter per target — `claude` (subagents, hook, root and nested `CLAUDE.md`, skill stubs) and `agents-md`
  (root `AGENTS.md` with index, a nested `AGENTS.md` per unit with its facts). Proximity loading — the closest
  file wins, which Codex, Cursor, Gemini CLI and Copilot all do — filled with measured facts and kept current.
  Detection from the repo, remembered in the state, overridable in `sherpa.toml [apply]`. Further adapters
  (Cursor rules, Copilot instructions) are new target values.
- **Never overwrite, only add** (ADR-0016): in the user's repo `apply` creates, appends and merges; it rewrites only
  its own unchanged bytes (hash in the state) and deletes nothing.
- **Dry run is the default** (ADR-0008). `sherpa apply` shows every file with `+ new`, `~ updated`, `= unchanged`,
  `! skipped` and the reason, then asks once; `--yes` for CI, `--dry-run` never asks. Selection: every `propose`
  unless rejected, every `skip` that was accepted (Terraform model, ADR-0013).
- **Ownership by block, not by file** (ADR-0013): a generated markdown file is seeded once; afterwards sherpa owns
  only the text between `sherpa:begin`/`sherpa:end` markers (facts, knowledge manifest, scope) and regenerates it
  on every apply; everything outside is the humans'. One hash per block in the state; a hand-edited block is
  skipped on its own. Whole-file ownership only for sherpa's scripts; `settings.json` gets hook entries merged.
  A file with no state record is never touched — `sherpa adopt` takes it over.
- **The outcome minimum belongs to `apply`** (ADR-0008): hook script + `settings.json` entries, label file
  `.sherpa/telemetry/outcomes.ndjson` (ignored by git), `harness_rev` = hash over everything sherpa owns plus the
  version. A rejected outcome entry is an error — a harness without a signal is not created.
- **The checker has one source** (`src/sherpa/check.py`, ADR-0013) and is deployed as a managed copy
  `.claude/scripts/sherpa-check.py` that delegates to an installed sherpa. `apply` rolls back when the write
  introduces a **new** FAIL; pre-existing FAILs are reported, never block.
- `sherpa status`: drift (`~ ! - ?`), checker findings, outcome counts per `harness_rev`; exit 1 only on FAIL.
- Multi-repo (M7): one workspace `sherpa.toml`, one state per repo, shared templates.
- **Determinism guarantee:** `apply` is a pure function `(plan, model, files, state) → actions`. No LLM, no
  network, no clock in file contents (the only timestamp is `applied_at` in the state); sorted output, hashes with
  normalised line endings. Proven: the second run is all `=` with an unchanged state and tree hash
  (`test_apply_is_idempotent_and_deterministic`). The same holds for `scan` and `plan` stage 1.

### 2.4 Auto-evals from the graph (the part the market does not have)

Golden questions with ground truth from `codebase-model.json`, no LLM invention — every question is a model field:

- "Which modules depend on `Shop.Core`?" → `modules[Shop.Core].dependents`
- "Which test project covers `Shop.Pricing`?" → `modules[Shop.Pricing].tested_by`
- "Which file is the hotspot in `Shop.Pricing`?" → `modules[Shop.Pricing].hotspots[0]`
- "What does `Shop.Api` depend on?" → `modules[Shop.Api].deps`

Every generated agent thus has a verifiable eval on day 0. The baseline is stored in the state; `status` reports
regressions. Questions whose answer changes with the next scan (hotspots) are regenerated on re-scan — they
measure currency, not memorisation.

### 2.5 Outcome channel and learning

The minimum (hook, label file, `harness_rev`) comes with the first `apply` (M3a ✅); evaluation (`sherpa status`:
labels per harness version, trend) in M5. Observed in practice: when the signal arrives after the features, every
execution stays `unknown` and nothing can be measured. Playbooks/instincts only once ≥ 30 labelled executions
exist. Learning without a signal is a promise, not a feature.

### 2.6 Adopt — take over existing harnesses, do not overwrite (ADR-0007, ADR-0017) ✅

Many target repos already have a `.claude/` or an `AGENTS.md` hierarchy — a mature one holds a dozen agents and
several librarians. The model is `terraform import`: an existing resource is brought into the state without
being changed. Built in M3c (`docs/commands/adopt.md`):

1. inventory of `.claude/**`, `.agents/**` and every `CLAUDE.md`/`AGENTS.md`, classified by path only (agent,
   skill, command, doc, hook, settings, script, eval, root, nested, unknown); git-ignored files are not the harness;
2. reconciliation against the plan's rendering: what equals the rendering is recorded as `generated` (this is
   the rebuild of a lost state — same `harness_rev` as `apply` wrote), a block that differs stays unrecorded
   (a hand edit and an older rendering are indistinguishable, and the console says so), base files are sherpa's
   by name, everything else is `origin: adopted` and never touched by `apply`;
3. links from adopted agents and docs to units — name, front matter name, then the unit path mentioned most
   (≥ 2, unambiguous) — and **covered** plan entries: `plan` shows `[covered by …]`, `apply` renders nothing for
   them, agents and proximity files point at the adopted doc; `decision: accept` overrides;
4. gaps from the same inventory: agent over budget without a manifest (rotation candidate), doc matching no unit,
   agent for a unit below the threshold, proposed owner docs with nothing there, unknown files.

Deliberately not done: `hand-edited: true` as a field (an adopted file is hand-edited by definition — `origin`
says it), evals per agent (no generic eval convention yet; M4), and any content-based classification.

### 2.7 What ships and what stays here (M2b ✅, ADR-0018)

The product is `src/sherpa/` — and only that. `pyproject.toml` owns the list (the package, the schemas, the hook
asset); `release.yml` builds the wheel `sherpa-harness` from it on every tag `v<version>`, installs it into a
fresh venv, runs `sherpa --version` and `doctor`, and attaches it to the GitHub release. Everything else in the
repository is development only: `tests/` with the goldens, `docs/` with this plan and the ADRs, the repository's
own harness under `.claude/`, `scripts/` and the vault. A customer machine sees the wheel, `sherpa doctor` on
first contact, and `sherpa self-update` for the next version — with a token through the Releases API, without
one through the tag's git URL. The daily hint runs in a background thread and prints only what an earlier check
cached: it can never slow or fail a command. Test corpus check: `doctor` on all four corpus repositories reports
`0 problems`; the guessed-trunk hint fires exactly on the clone without `origin/HEAD`.

## 3. Milestones (vertical slices, foreign repos)

The README roadmap mirrors this table: the same rows in the same order (done by merge order, open by the order in
the status line), one or two sentences per row there, the full reasoning and the acceptance here.

| M | What | Acceptance |
|---|---|---|
| M0 ✅ | skeleton, ADRs, plan (this doc) | `sherpa --version`, tests green |
| M1 ✅ | scanner T0 (every language): trunk, churn, hotspots, file tree, generated files, JSON schema | fixture repo → identical JSON on two runs; 58 tests, 98 % coverage; a 15k-file monorepo in 2.5 s |
| M1a ✅ | scanner T1: modules from manifests (6 ecosystems), in-repo deps, `tested_by`, churn per module, conventions | polyglot fixture (`tests/test_t1_modules.py`); 105 tests, 99 %; ~50 modules of a 15k-file monorepo in 2.6 s |
| M2 ✅ | `plan` stage 1: units, rank + floor, generator families → skills, visible no's within reach, `decision` keeping, plan schema, `[plan]` config | goldens on the polyglot and the active fixture (`tests/goldens/`); evidence = model fields only (tested); large monorepo: 2 librarians, test infra detected, migrations project → skill; 5-module fixture: 1 agent; 173 tests, 99 % |
| M3a ✅ | `apply` with dry-run default, managed blocks, state, **outcome minimum** (hook, labels, `harness_rev`), checker with rollback, `status`, `check` | second run = all `=`, state and tree hash unchanged; hand-edited blocks skipped, other blocks still regenerated; rollback on a new FAIL tested; 213 tests, 98 %; 61 files for a 15k-file monorepo plan in 0.15 s |
| M3t ✅ | target layer: neutral core under `.agents`/`.claude`, adapters `claude` and `agents-md`, nested proximity files, `[apply]` config, ask when both homes exist | five-module fixture with both targets: 18 files, second run all `=`; existing root and nested `AGENTS.md` get the block appended; a 122-module corpus repo: 243 files in 0.2 s; 222 tests |
| M3c ✅ | `sherpa adopt` (§2.6) — reads `.claude/`, `.agents/` and AGENTS.md hierarchies; covered entries; rebuildable state (ADR-0017) | existing-harness fixture: 6 files adopted, 0 bytes changed, 2 entries covered, gaps listed; torn state rebuilt with the same `harness_rev`; a 16-module corpus repo with 12 hand-written AGENTS.md: 0.22 s, 32 files rebuilt after a lost state; 230 tests, 98 % |
| M2b ✅ | distribution + onboarding: `sherpa doctor`, `release.yml` (tag → wheel → GitHub release), `sherpa self-update`, daily update hint (`SHERPA_NO_UPDATE_CHECK`), GitHub Releases as the index (ADR-0018) | `doctor`: nine checks with a fix each, exit 1 only on a fail; `self-update` through the owning installer (uv/pipx/pip), git-tag fallback without a token via `git ls-remote` and the wheel under its PEP 427 name (ADR-0035, F17), clones refused; the hint is a background thread plus cache — zero wait; 282 tests, 98 % |
| M3d ✅ | low-hanging fruit from the retro (§7) plus the two preconditions the review found (§8): stamp without rev (ADR-0019) with legacy-stamp recognition in `adopt` (ADR-0022), model v4 with `sub_dirs` and sub-units by the depth rule (ADR-0020), change coupling with a size cap (ADR-0021), `plan --accept/--reject` by address, root index capped at 20 by rank, privacy note for the hook, session-built fixtures | `test_trunk_move_without_activity_changes_no_block`: two revs, no activity → `nothing to do.`; `test_adopt_recognises_an_older_stamp…`: 0.5.0 bytes → lost state → adopt → apply → `nothing to do.`; Sherpa's own plan lists `src/sherpa/apply`, `plan`, `scan` as units; `test_root_index_is_capped_and_ordered_by_rank`; suite 12 s → 7 s on Linux; 296 tests, 98 % |
| M3e ✅ | fruit of the whole-product review (§10): `status` names a stale plan and has `--json`, `doctor --json`; two manifests in one directory decided by language share (ADR-0025, closes Q4); coupling without the root catch-all (ADR-0026); the depth rule on a dominant root module (ADR-0027); proximity-file budgets in C7 (ADR-0029); the M5 denominator decided (ADR-0028); the architect agent's stale facts removed | `test_status_reports_a_stale_plan_and_json`; `test_find_modules_two_manifests_the_language_with_more_files_wins`; `test_coupling_excludes_the_root_catch_all`; `test_sub_units_for_a_root_module_only_when_alone_or_dominant`; `test_c7_proximity_file_budgets_in_bytes`; `test_status_names_adopt_on_a_foreign_state_schema`; corpus: the polyglot root is `python` now, coupling rows 21 → 11 and 15 → 13, 9 sub-units on the dominant root, C7 fires on a 9.9 KB nested file; 305 tests, 98 % |
| M3f ✅ | write safety: `apply` never overwrites a file that changed between the preview and the write — `write()` re-reads and compares with the preview's read, skips with `changed since the preview` and keeps the record, a rollback touches only what was written (ADR-0030); a path with a symlink in it is never written through, in or out of the repository (ADR-0031); every file is written whole or not at all and an `OSError` half-way rolls back what was written (ADR-0032); `adopt` records a differing base file as yours instead of sherpa's by name (ADR-0033, amends 0017 §2; §10.4); `adopt` ignores a stale plan and `plan`, `status`, `adopt` run on a torn state with the way out on stderr — only `apply` refuses both (ADR-0034, F16); a preview (`apply --dry-run`, `adopt --dry-run`, `status`) with two homes and nothing decided assumes `.agents` and says so instead of refusing, a write still asks or refuses (ADR-0036, F18); a home or `.claude/` that is a repository of its own is named with one note, never refused (ADR-0037, F19) | `test_write_skips_a_file_that_changed_since_the_preview` (managed, blocks, hooks; prose outside the markers survives), `test_write_skips_a_file_that_appeared_since_the_preview`, `test_rollback_never_touches_a_file_skipped_since_the_preview`, `test_plan_never_writes_through_a_symlink`, `test_plan_never_writes_through_a_symlink_to_a_sibling`, `test_write_skips_a_path_that_became_a_symlink_since_the_preview`, `test_write_rolls_back_when_a_write_fails_half_way`, `test_write_names_what_a_failed_rollback_left_behind`, `test_write_is_atomic_per_file`, `test_adopt_keeps_hand_edits_in_blocks_and_in_base_files`, `test_adopt_and_plan_run_on_a_torn_state_after_the_trunk_moved`, `test_resolve_layout_preview_assumes_agents_when_both_homes_exist`, `test_cli_dry_run_assumes_a_home_and_the_write_refuses_without_a_terminal`, `test_resolve_layout_names_a_target_directory_that_is_a_repository_of_its_own`, `test_cli_apply_names_a_nested_repository_in_the_dry_run_and_the_write`; 326 tests, 98 % |
| M3h | `hermes` target (ADR-0023): third entry of `TARGETS`, detected by `hermes` on the `PATH`, `~/.hermes/` or `.hermes.md`; thin on top of `agents-md` — appends the root block to `.hermes.md`/`HERMES.md` when it exists (first match wins there), `version: 1` in every skill's front matter (neutral core), one outcome hook script for both payload shapes (`PostToolUse`/`Stop` and `post_tool_call`/`on_session_end`), `apply` prints the `~/.hermes/config.yaml` hook snippet once, `doctor` checks `hermes-hook` and `hermes-trust` (`hermes skills trust`), `status` counts labels from both runtimes per `harness_rev` | five-module fixture with targets `claude, agents-md, hermes`: same files as before plus `version:` (goldens on purpose), a fixture with `.hermes.md` gets the block appended and `AGENTS.md` untouched; hook test with a Hermes payload → label with the same `harness_rev`; `doctor` on a machine without Hermes: no new line; corpus: `hermes` launched in one repo loads the nested `AGENTS.md` and lists the skills after `trust`; C7 (ADR-0029) fires on the corpus repository with an oversized nested file. Verified in Hermes' source (§10): the skill loader does not require `version` in the front matter — keep `version: 1` only if the skills hub needs it, verify before building |
| M5 | outcome evaluation (ADR-0028): `status` shows labels per `harness_rev` with `n` and the share of `unknown` (records with `harness_rev_at_stop` left out, ADR-0040); a comparison between two revisions only from `outcome_min_n` (30) labelled executions each; Q14's fruit (test and build commands per unit, a `status` line for adopted files changed since adopt) | first 10 executions on a corpus repo with a label ≠ `unknown`; the `unknown` share visible from the first label; the comparison line appears at 30 per revision and names the missing count below; `status --json` carries the counts |
| M7a | runtime plugins (ADR-0024): a Claude Code plugin (`.claude-plugin/`, marketplace) and a Hermes bundle (`hermes bundles`, tap) generated from one source under `plugins/`, released with every tag; commands `/sherpa-doctor`, `/sherpa-plan` (reads the plan entry by entry, asks, writes the answer with `--accept/--reject`), `/sherpa-apply` (dry run shown, then `--yes` after the user's yes), `/sherpa-status`; thin — the CLI does the work, no hook in the plugin | plugin manifests validated in a test; `claude plugin install` from the release and `/sherpa-plan` on the five-module fixture ends with the same `harness-plan.yaml` as the CLI with `--accept/--reject`; Hermes: `hermes skills install` of the bundle lists the four commands; a missing CLI produces the install line, nothing else |
| M6-lite | provider layer (ADR-0004): thin, framework-free — bring your own key, local models through the OpenAI API (vLLM, Ollama, OpenRouter), Anthropic natively; no LangChain, no agent framework; used by M4 evals and M6 first | the same schema pass through a local OpenAI-compatible model and through Anthropic; a missing key produces one line and the stage-1 plan unchanged |
| M4 | auto-evals from the graph, `status` with baseline | eval run on the fixture ≥ 90 %; regression is reported |
| M6 | `plan` stage 2: LLM enrichment on top of M6-lite — comments only, stage-1 entries never change | plan diff stage 1 vs. 2 documented; the same schema pass with both providers; stage-1 entries unchanged |
| M3b | adapters `dotnet` + `python` (T2: anchors, patterns) — **proposed after M6-lite** (§7.3) | a scan yields the anchors a harness checker verifies today; owner docs get anchors |
| M7 | librarians, multi-repo (`/sherpa-plan` moved to M7a) | a second repo in the workspace |

Every milestone ends with: CI green (`.github/workflows/ci.yml`: pytest on Linux for pull requests, Linux and
Windows on `main`, macOS weekly, all three on a manual run — ADR-0037; coverage ≥ 90 %, ruff), docs updated (`plan.md`, the concept doc in `docs/concepts/`, the command reference in `docs/commands/`,
`docs/index.md`), Sherpa applied to itself (`sherpa status .` clean — the repo carries its own harness under
`.claude/`), Andrei sees the diff before the commit. The ritual is `.claude/skills/milestone-step/SKILL.md`.

Test corpus: foreign open-source repositories in four ecosystems (.NET, Java, Python, Node; 50 to 20k files)
cloned locally next to the repo, never checked in and never named in it. Every slice is smoke-tested on all of
them (scan, plan, apply dry run, check; artefacts deleted afterwards). Repos with an existing harness are
regression cases: a Sherpa scan must find the owners defined there.

## 4. Deliberately NOT proposed

- **Rust core** — see ADR-0001; flip criterion there.
- **Vector/semantic search in the scanner** — graph + churn suffice for owner candidates; semantics later, if M2
  shows that module boundaries are guessed wrongly.
- **Knowledge-base projections** (Obsidian and the like) — project-specific, adapter candidate after M7.
- **GEPA/DSPy prompt optimisation** — only once evals (M4) and outcome (M5) run stably.
- **LangChain / LangGraph** — see ADR-0004: one LLM call with schema validation needs no graph runtime; flip
  criterion there.
- **Skill proposals without code evidence** — no skill "in stock"; only with T2 patterns (M3b) or generator
  evidence (M2).
- **External packages in the dependency graph** — for owner boundaries only what lives in the repo counts
  (`docs/concepts/scan.md`).

## 5. Test strategy

Many tests, small units, everything reproducible:

| Level | What | How |
|---|---|---|
| Unit | every function in `src/sherpa/` | `pytest`; fixture repos are built **programmatically** (`tests/conftest.py`), fixed git dates/authors → same SHAs |
| Determinism | `scan`, `plan` stage 1, `apply`, `status` | two runs, byte comparison (scan ✅, plan ✅) or tree hash (apply ✅) |
| Snapshot | `harness-plan.yaml` and console view per fixture | `tests/goldens/` (checked in), `SHERPA_UPDATE_GOLDENS=1` refreshes after an intended rule change; version and rev are normalised |
| Self-test | checker | one positive and one negative case per rule (`tests/test_check.py` ✅); the deployed copy standalone and delegating |
| Corpus | real repos under `tests/corpus/` (ignored) | smoke: scan runs through, schema valid, runtime < 60 s; never in CI |
| Schema | `codebase-model`, `harness-plan`, `harness-state` | JSON Schema under `src/sherpa/schemas/`; validated on every read and write by the stdlib validator `sherpa/schema.py` (ADR-0036); `jsonschema` (dev extra) is the reference the tests compare it with on one input matrix |

Gate: coverage ≥ 90 % for `src/sherpa/`, `pytest -q` green before every milestone. Status M3f: 326 tests, 98 %.
The conftest sets `SHERPA_NO_UPDATE_CHECK` and a temporary cache directory for every test, in-process and in
subprocesses: no test reaches the network.

## 6. Open questions (decision: Andrei)

1. Which foreign repos form the first corpus (target: ≥ 3 languages)?
2. ~~How much of a production harness checker is generic?~~ Decided with M3a: eight generic rules (front matter,
   manifest paths, file links, block markers, hook wiring, budgets, drift — `docs/concepts/harness-apply.md`); code
   anchors and owner-move directives are adapter/M3b material.
3. Structured output: which providers enforce JSON Schema natively (vLLM: `guided_json`; Anthropic: tool use)?
   Relevant from M6.
4. ~~Two manifests in the same directory: today the alphabetically first wins — is that enough in the corpus?~~
   Decided 2026-09-17 (ADR-0025): it was not — the corpus root with 6.5k Python and 2.3k TypeScript files was
   `node`; the kind with more source files under the directory wins, a tie by manifest name.
5. ~~Package index for M2b?~~ Decided 2026-09-17 (ADR-0018): GitHub Releases through the API with the user's
   token, git-tag URL as the fallback; PyPI at the public release. No third service.
6. ~~Owner-doc floor by files?~~ Decided 2026-09-17 (ADR-0014): `owner_doc_min_files = 5`, a dependent overrides
   the floor; small units are listed as no's and counted in a note so the reader sees them.
7. ~~Order: M2b before M3?~~ Decided 2026-09-17: M3 first (the product truth "creates" needs `apply`); M2b after
   `adopt`.
8. ~~Provider-neutral output?~~ Decided 2026-09-17 (ADR-0015): neutral core + targets `claude`, `agents-md`;
   Cursor (`.cursor/rules/*.mdc`, `globs`) and Copilot (`.github/instructions/*.instructions.md`, `applyTo`)
   are the next adapters once a corpus repo uses them.
9. ~~Interactive per-entry approval in the CLI was rejected for M3a (ADR-0013); `/sherpa-plan` in Claude Code (M7)
   is the better place. Reopen if the YAML editing turns out to be the friction point in customer tests.~~
   Decided 2026-09-17 (ADR-0024): the per-entry approval is the plugin's `/sherpa-plan` in M7a; the CLI keeps
   `--accept/--reject` for scripts and CI.
10. ~~Stamp without the rev (§7.1 G1)?~~ Decided 2026-09-17 (ADR-0019): the stamp is `as of <date>` only; the rev
    stays in the state and the plan header. Implemented in M3d.
11. ~~Sub-units for single-manifest repositories (§7.1 G2)?~~ Decided 2026-09-17 (ADR-0020): the depth rule, with
    `[plan] units = […]` in `sherpa.toml` as the override. Implemented in M3d.
12. ~~Milestone order (§7.3)?~~ Decided 2026-09-17: M2b → M3d → M5 → M6-lite → M4 → M6 → M3b → M7; revision 10
    inserted M3h and M7a before M5, revision 11 (§10 F6) put M5 back before M7a: M3h → M5 → M7a → …. Tree-sitter
    (M3b) stays an optional extra (`sherpa[adapters]`), never a core dependency; it moves forward only if M4
    evals from the graph score < 90 % on the corpus or a customer needs skills from code patterns.
13. Coupling between sub-units of a single-manifest repository (ADR-0021 measures modules only): worth a model
    field once a corpus repository with sub-units shows a pair above the floors? Measure first.
14. Remaining fruit from §7.2 not in M3d: test and build commands per unit in the facts; a `status` line for
    adopted files changed since adopt. Both small; schedule with M5, which touches `status` anyway.
15. **Owner-doc floor for sub-units by files is the wrong metric for Python packages.** Sherpa's own `plan` (3
    files, ~1.0k LOC) and `scan` (4 files, ~0.9k LOC) are reasoned no's under `owner_doc_min_files = 5`, while
    they carry most of the logic; the repository's hotspot score would have named them first. ADR-0014 was
    calibrated on modules (a three-file module is a tool), not on packages with few large files. Proposal: a
    second way over the floor for sub-units only — ≥ 5 files **or** ≥ 500 LOC — as an amendment to ADR-0014,
    with the LOC value in `sherpa.toml`. Decide after one more corpus repository with sub-units (Q13).

16. **Hermes hook wiring is global, not per repository** (`~/.hermes/config.yaml`; ADR-0023 makes it a `doctor`
    check with the snippet as the fix). Is a hint enough for the outcome minimum (ADR-0008), or should `status`
    show `outcome channel: hermes not wired` as a warning until the first Hermes label arrives? Recommendation:
    the `status` warning — it is the one place a team looks after `apply`, and it disappears by itself.
17. When a repository carries both `.hermes.md` and `AGENTS.md`, Hermes loads only the first. Append the block
    to `.hermes.md` (ADR-0023) or print a hint that `AGENTS.md` is shadowed? Recommendation: append, and say
    so in the dry run — never overwrite, but never let the harness be invisible either.

18. The plugin's `/sherpa-plan` asks per entry — the interaction Q9 rejected for the CLI. Which order: proposals
    first, then no's within reach, dormant last? And should a `reject` on a proposal ask for a one-line reason
    that lands in the plan's `decision_note`? Recommendation: that order, and yes to the note — it is the
    evidence the next re-plan shows next to the struck entry.

19. ~~Order M3h → M7a → M5, or M5 before the plugins (§10 F6)?~~ Decided 2026-09-17: M3h → M5 → M7a — the plugins
    distribute a claim M5 has to prove first (§9).
20. ~~Manifest tie-break by language share (§10 F2)?~~ Decided 2026-09-17 → ADR-0025.
21. ~~Root module excluded from coupling partners (§10 F3)?~~ Decided 2026-09-17 → ADR-0026.
22. ~~Depth rule for a dominant root module (§10 F4)?~~ Decided 2026-09-17 → ADR-0027 (`root_share = 0.5`); Q15's
    LOC floor stays open and now matters for more repositories.
23. **The checked-in plan churns on every trunk move — the harness no longer does.** Measured on this repository
    between two merges: `harness-plan.yaml` 37 +/38 − lines (header rev, `as_of`, every evidence number) while
    `apply` would write zero lines (ADR-0019). Terraform never checks a saved plan in; the durable part is the
    decisions. Options: keep ADR-0005 (the diff is the audit trail of what the numbers were), or split the
    decisions into a small checked-in `harness-decisions.yaml` and let the full plan join the model as an
    ignored artefact (touches `yamlio`, `adopt`'s covered marks, the docs; M). Recommendation: keep, with this
    flip criterion — a corpus team reviews the plan diff as noise.
24. ~~M5 denominator (§10 F8)?~~ Decided 2026-09-17 → ADR-0028: `n` and the `unknown` share per revision from the
    first label, a comparison only from 30 per revision.
25. ~~Diagrams as code — which format, and where does a generated one live?~~ Documentation half decided 2026-09-17 → ADR-0041 (`docs/architecture/`, Mermaid text); the generated per-unit graph stays M3g.
    Original question: **Diagrams as code — which format, and where does a generated one live?** Two uses: Sherpa's own
    mechanisms in `docs/concepts/` (scan → model → plan → apply → state, the ownership decision, the write path
    with compare-and-swap and rollback), and per-unit graphs rendered from the model into the harness (the
    unit, its in-repo deps, coupling partners with the share on the edge, hotspot count as a badge).
    Recommendation: **Mermaid, emitted as text and never rendered by Sherpa** — MIT, a fenced block that GitHub,
    GitLab, Obsidian (the vault) and MkDocs (`mkdocs-mermaid2-plugin`, MIT, client-side) render without a tool,
    readable by an agent as plain text, no dependency in the wheel (ADR-0001, no network). Rejected: Graphviz
    (EPL-1.0 binary; a `--dot` export stays an option for large graphs, the user renders), PlantUML (GPL-3
    core, Java), D2 (MPL-2.0 binary), Kroki (a network service). Per unit, never one global graph — on a
    122-module repository that is unreadable and useless to the agent reading one owner doc; a capped root map
    like the index (ADR-0021) at most. The generated graph gets **its own block** (`graph`), so a hand-edited
    facts block does not freeze it and vice versa (ADR-0013 per-block ownership). Sorted ids → byte-stable →
    goldens on the fixtures. A slice after M3f (M3g), one ADR; changes nothing in the order M3h → M5.

Decided (2026-09-17): the `hermes` target and the reordered direction → ADR-0023; runtime plugins from one
source, thin, no hook in the plugin → ADR-0024; manifest tie-break → ADR-0025; coupling without the root
catch-all → ADR-0026; sub-units for a dominant root module → ADR-0027; the M5 denominator → ADR-0028;
proximity-file budgets → ADR-0029.

Decided (2026-09-16): plan format YAML and check-in of plan/state → ADR-0005; generator principle → ADR-0011;
units, visibility, decision keeping → ADR-0012. Decided (2026-09-17): state as a rebuildable index, atomic
writes, adopt as the rebuild → ADR-0017; block ownership, single-source checker,
Terraform-style selection → ADR-0013; owner-doc floor by files → ADR-0014; target layer → ADR-0015; never
overwrite, only add → ADR-0016; distribution through GitHub Releases → ADR-0018; stamp without rev → ADR-0019;
sub-units with override → ADR-0020; change coupling with a size cap → ADR-0021; adopt recognises older
renderings → ADR-0022.

## 7. Retro after M3c (2026-09-17) — what the numbers say against the plan

Method: every claim below was measured on the fixtures, on Sherpa's own repository or on the corpus (four
ecosystems, 54 to 20k files); nothing is a feeling. Findings are ordered by cost of ignoring them. The retro
after every milestone runs as the read-only skill `.claude/skills/architect-review/SKILL.md`
(`/architect-review [focus]`): evidence per finding, the market answer by name, nothing implemented — Andrei
decides what enters this plan.

### 7.1 Four gaps the plan did not see

| # | Finding | Evidence | Consequence |
|---|---|---|---|
| G1 | **Every trunk move rewrites every block.** The facts stamp is `origin/main@<rev>, as of <date>` and sits in every facts block, proximity block, agent scope and skill (`render.py`, four places). | A merge with no activity in a unit still changes its block (the rev moved); `apply` then reports `~` for all 243 files of the 122-module repo. The state's `plan.rev` already records the rev. | Harness churn in every PR after `apply`; teams will stop running it. Fix: stamp = `as of <date>` only; the rev stays in `state.json` and the plan header. Blocks then change only where a number changed. One line plus goldens; an ADR because it touches the determinism story (the date still moves with every scan — acceptable, it is the window end). |
| G2 | **Single-manifest repositories get one unit.** `units_of` takes modules from manifests and adds depth-1 directory units only when no root module exists. A repository with one `pyproject.toml`/`package.json` at the root — the most common shape — is one unit. | Sherpa itself: `scan`, `plan`, `apply` are the subsystems; the plan says `1 owner-doc sherpa-harness`. The 1-module corpus repo: the same. The plan's strongest case (units, ranks, no's) never appears there. | Rule to add (ADR): when the root module is the only module, directory units come from the first depth below the source root where ≥ 2 directories meet `owner_doc_min_files` (Python: packages with `__init__.py`; generic: directories), tests excluded. The root module keeps the repo-level owner doc. |
| G3 | **The root `AGENTS.md`/`CLAUDE.md` index grows with the repo and is loaded on every turn.** | 122-module repo: 76 index lines in the root file → ~1.2k tokens in every prompt of every runtime that reads it. `MAX_NAMED = 12` exists for plan notes, nothing for the index. | Cap the index at the top N by rank (N = 20) plus one line "and 56 more under `<home>/docs/modules/`" — the runtimes load the nearest file by themselves, the index is for discovery only. |
| G4 | **Change coupling is measured nowhere, although it is the fact an agent needs most when it lands in a module.** `git log --name-only` is already parsed for churn (`t0_git.py`); the commit → modules mapping is free. | Tornhill's temporal coupling: "in 15 of 24 commits touching `pay`, `core` changed too (62 %)". Neither `deps` (static) nor hotspots (per file) carry this. Corpus check: cheap to add, deterministic per rev. | Model v4 field `coupling` per module (top 3 partners with count and share, floor: ≥ 5 shared commits and ≥ 30 %), one row in the facts and proximity blocks: `changes together with`. The first measured fact the market's AGENTS.md files do not have. |

### 7.2 Low-hanging fruit (each < half a day, all deterministic)

| Item | Why now | Where |
|---|---|---|
| `sherpa plan --accept <kind>:<target> --reject …` | today a decision means editing YAML; CI and scripts have no way to decide. Q9 rejected an interactive prompt, not flags. | `cli.py`, `yamlio.merge_decisions`; keys as in the state (`agent:pay`) |
| test and build commands per unit in the facts | T1 knows the ecosystem (`pytest`, `dotnet test <csproj>`, `npm test`, `go test ./...`, `cargo test`, `mvn test`): the line an agent runs first. `tested_by` names the module, not the command. | `render.facts_rows`, `proximity_block`; per-ecosystem table in `t1_modules` |
| privacy note for the outcome hook | `outcomes.ndjson` stores the first 160 characters of every prompt locally; documented nowhere as such. Git-ignored, but a team should know. | `docs/commands/apply.md` (hook section), `concepts/harness-apply.md`, the hook's docstring |
| `sherpa status` line for adopted files that changed | today silent by design; a count ("3 adopted files changed since adopt") costs nothing and tells the team when to re-adopt for a fresh `harness_rev`. | `status.report` |
| Windows CI at 7.5 min vs. 38 s on Linux | every fixture builds a git repository with dozens of subprocess calls; `pytest -x` masks nothing, but the feedback loop is slow. | session-scoped fixture repos copied per test (`shutil.copytree` is ~50× cheaper than the commits) |

### 7.3 Order of the remaining milestones — a proposal

The plan runs M3b (language adapters, tree-sitter) before M4 (evals), M5 (outcome evaluation) and M6 (LLM).
Measured against value per effort that order is wrong:

- M3b is the largest slice and the plan itself says T0+T1 suffice for owners, churn and evals; anchors and code
  patterns improve skills, not the harness's spine.
- M4's eval runner and the §0 runtime both need a model binding; M6 builds it. Building M6's provider layer
  first — thin, `complete(messages, schema) → dict`, OpenAI-compatible plus Anthropic, no enrichment yet —
  gives M4 its runner and the runtime its first brick.
- M5 (labels per `harness_rev`, trend, share of `unknown`) is pure arithmetic over data the hook already
  collects; it is small and it answers "does the harness help?" — the product's central claim.

Decided (Andrei, 2026-09-17): **M2b → M3d → M5 → M6-lite (provider layer) → M4 (evals with the runner) → M6
(enrichment) → M3b → M7** (§6 Q12).

### 7.4 What holds

- Determinism, trunk discipline, never overwrite, one owner per fact, dry run first: every test that proves them
  is still green after M3c, and adopt's rebuild reproduced `apply`'s `harness_rev` on the first try.
- Speed: the largest corpus repo scans in 3.8 s, plans in 0.12 s, applies in 0.2 s, adopts in 0.37 s.
- The corpus rule (four foreign repos, never named) caught the Windows path bug and the empty-state case that
  the fixtures did not.

## 8. Retro after M2b (2026-09-17) — the review before M3d

Method: the read-only skill `architect-review` with focus M3d (§7 method); every claim measured on the fixtures,
on Sherpa's own repository or on the corpus. Two of the six M3d items carried a precondition the retro in §7
had not seen; both were built into M3d before it shipped.

### 8.1 Gaps

| # | Finding | Evidence | Consequence |
|---|---|---|---|
| G5 | **ADR-0019 would have broken `adopt`'s rebuild for every harness written before it.** `adopt` decides ownership by "equals the current rendering"; after the stamp change no 0.5.0 block equals its 0.6.0 rendering. | `adopt.py` reconcile: a differing block "stays"; no test for "old stamp, new sherpa". | A lost state rebuilt after the upgrade would freeze the whole harness as hand-edited, silently. Built: `LEGACY_STAMPS` + `modernize_stamp` (ADR-0022), one end-to-end test. |
| G6 | **The sub-unit rule had no data to run on.** `DirStat` stopped at depth 2; Sherpa's own sub-units are depth 3, the Python default `src/<pkg>/<sub>` layout too. | `t0_git.py` `DIR_DEPTH = 2`; `sherpa plan .` → `1 owner-doc sherpa-harness`. | ADR-0020 could not be implemented in `plan/` alone. Built: `sub_dirs` per module in the model (v4), depths 1–4 relative to the module path, with source-file counts and the package flag. |
| G7 | **Naive change coupling is dominated by squash merges.** Sherpa's trunk: 14 commits in 90 d, every one touches docs, tests, README and several modules → 100 % coupling everywhere. GitHub's default merge option produces this shape. | `git log origin/main --no-merges --name-only` on this repository. | A `changes together with` row that reads 100 % is wrong. Built: size cap max(5, ⌈modules/2⌉) with the skipped count in the model (ADR-0021). |
| G8 | **The index cap needs a rank, the index had none.** `agents_md_targets` sorted nested files alphabetically; `plan.ranking` was unused in `apply`. | `render.py` `sorted(nested, key=scope)`. | A cap on an alphabetical list keeps `a…` and drops the hotspot. Built: order by `ranking.commits_90d`, top 20, "and N more". |

Seen in the dogfood after the slice (Sherpa's own harness, first sub-unit `src/sherpa/apply`), fixed in the
same PR: the sub-unit facts block had four rows and no hotspots, although `git.files` carries them — now
hotspots under the path and the test files naming it; the root doc counted the sub-units' files without
saying where they are described — now `files / LOC … — N files in K sub-units, described in their own owner
docs` plus a `contains` row with links. What stays open is the floor (§6 Q15).

### 8.2 Fruit taken and left

| Item | Status | Where |
|---|---|---|
| Windows CI 7–8× Linux (4m33s / 5m46s vs. 43 s / 45 s on PR #11) | done first — session-built fixtures copied per test | `tests/conftest.py` `copy_repo`, `_session_repo` |
| `plan --accept/--reject` with one address format across plan, state and CLI | done — `Entry.address`, `yamlio.decide` | `plan/__init__.py`, `plan/yamlio.py`, `cli.py` |
| privacy note for the outcome hook | done — hook docstring, `commands/apply.md`, `concepts/harness-apply.md` | — |
| test/build commands per unit; `status` line for changed adopted files | left — §6 Q14, with M5 | — |
| state schema-version read-tolerance test (review #6) | left — the first state bump will need it; `state.py:69` names `adopt` as the way out already | — |

### 8.3 What holds

- Idempotence and determinism: `test_apply_is_idempotent_and_deterministic`; goldens changed only where the stamp
  and the index wording changed, in dedicated commits.
- Never overwrite, hand edits stay: `test_adopt_keeps_hand_edits_and_refreshes_base_files_by_name` — now with the
  unhedged message `(hand edit)`.
- The release path: v0.5.0 tag → `release.yml` green on the first run → wheel on the release → `self-update
  --check` reports current from the live API.
- Corpus: `doctor` 0 problems on all four repositories. Coupling on the three multi-module ones (16, 79 and
  122 modules): 21, 7 and 15 partner rows above the floors, one commit above the cap; the single-module one gets
  two sub-units at depth 1 by the rule. Sherpa's own repository: three sub-units at depth 3, one above the
  owner-doc floor, two listed as small units — exactly ADR-0014's reasoned no's.

### 8.4 Innovation candidates confirmed

1. **Change coupling as a harness fact** — real now that the cap is in; no AGENTS.md generator in the market
   carries it. Next proof: a corpus repository with a pair above the floors, quoted in the README from a golden.
2. **Zero harness churn when nothing changed** (ADR-0019) — Terraform's "no changes" for documentation;
   `test_trunk_move_without_activity_changes_no_block` is the proof, the README shows the line.
3. **`adopt` as config migration** (ADR-0022) — Renovate migrates config in place; Sherpa understands its own
   older renderings instead. The pattern list is the contract for every future block change.

## 9. Market position (2026-09-17) — Claude Code, Hermes Agent, and what neither builds

Question asked: can Sherpa be better than Claude Code or Hermes Agent? As a runtime: no — Claude Code has the
model vendor behind it, Hermes Agent (Nous Research, open source since 2026-02) crossed 175k GitHub stars in four
months with a self-improving loop, three-layer memory, self-written skills and multi-provider bindings. A
one-person product does not win that race, and §1 already lists a runtime of its own as a non-goal for v1.

As the layer underneath both: yes, and neither builds it.

| The runtimes | Sherpa |
|---|---|
| **consume** `CLAUDE.md`/`AGENTS.md`/skills; neither measures whether the harness helps | outcome labels per `harness_rev` — "does version X succeed more often than Y" is a number (M5) |
| Hermes learns from experience: LLM prose, per person, not reviewable | facts from `git log`, deterministic, reviewed in the PR like code, per team and repository — the "plausible-but-wrong drift" §1 rejects |
| each runtime binds the harness to itself | neutral core plus one adapter per runtime (ADR-0015); teams run mixed runtimes |
| no plan, no state, no adopt | Terraform's model: diff before effect, never overwrite, a rebuildable state |
| no evals from the dependency graph | M4 — the part the market does not have (§2.4) |

Terraform's position, not the cloud's. The threat is real and cheap: both runtimes could ship "plan from git"
in a sprint (`/init` and auto-memory exist). What is expensive to copy is the discipline — state, adopt without
overwrite, managed blocks, the outcome channel, neutrality — so the order M3d → M3h → **M5** is right: prove the
central claim (the harness helps, measured) before the market asks.

Consequence taken (ADR-0023): independence is entered through Hermes, not against it. Measured on 2026-09-17
against Hermes' documentation: it loads the merged `AGENTS.md` chain from the git root down with nested files
discovered progressively, reads `<root>/.agents/skills/*/SKILL.md` in the agentskills.io layout, and runs shell
hooks with the same JSON-on-stdin shape as Claude Code's — three of the four things the `agents-md` target and
`home: .agents` already produce. The gaps (skill `version`, the `.hermes.md` precedence trap, global hook wiring,
`doctor`) are M3h; the corpus smoke test with a real `hermes` launch is its acceptance.

## 10. Retro after M3d (2026-09-17) — the whole product, before M3h

Method: `architect-review` without a focus (§7 method): the suite, `ruff`, `status`/`apply --dry-run` on this
repository, a scratch clone re-scanned and re-planned, the four corpus repositories through `scan`, `plan`,
`apply --dry-run`, `check`, `doctor`, and Hermes Agent's public source read for the premises of ADR-0023.
Eleven findings; six built as M3e in the same day, one decided as an order change, one recorded as Q23.

### 10.1 Gaps

| # | Finding | Evidence | Consequence |
|---|---|---|---|
| F1 | **`status` was silent on a stale plan; `apply` refuses on it.** | `cli.py` called `_refuse_stale` for `apply` and `adopt`, not for `status`. On this repository `status` said `drift: none` while `apply` refused — through two merges, and the milestone-step gate "status clean" passed. | Built: `plan: current` / `plan: stale — origin/main moved a → b since \`sherpa plan\`` as the second line, a warning, never an exit code; `test_status_reports_a_stale_plan_and_json`. |
| F2 | **Two manifests in one directory: the alphabet decided, wrongly** (Q4). | Corpus polyglot root: 6.5k `.py`, 2.3k `.ts`, kind `node`; `sub_dirs.source_files` counted node extensions → a 4.5k-file directory showed 6 source files. | Built: ADR-0025, the kind with more source files under the directory wins. |
| F3 | **Coupling with the root catch-all was tautological.** | Same repository: three of the four most active modules named the root module (64 % of the files) as first partner, shares 0.45–0.74, `skipped_commits: 0`. | Built: ADR-0026 — the root module next to others is excluded and named in `coupling.excluded`; rows 21 → 11 there, 15 → 13 on the 122-module repository. |
| F4 | **ADR-0020's trigger missed "root package + a few sub-packages".** | Same repository: 16 modules, root module 8.8k of 13.6k files, `sub_dirs` 797 entries with depth-1 directories of 4.5k, 1.2k, 788 files — one owner doc, one agent. | Built: ADR-0027 — the depth rule runs on a root module holding ≥ `root_share` (0.5) of the files; 9 sub-units at depth 1 there. |
| F5 | **The repository's own architect agent contradicted the ADRs.** | `architect.md` promised "an agent in its own right (a runtime like Claude Code or Hermes)" against ADR-0023 §5, listed exit codes 0/1/2 (`cli.py`: 0/1) and model v3 (v4). | Built: the direction paragraph points at §0, the map carries no version numbers. Invariant 3 restored where it is stated. |
| F6 | **M7a before M5 delayed the central claim.** | §9: "M3d → M3h → M5 is right: prove the central claim before the market asks"; the rev-10 status line put M7a between. | Decided (Q19): M3h → M5 → M7a. |
| F7 | **The checked-in plan churns on every trunk move.** | 37 +/38 − lines in `harness-plan.yaml` between two merges, zero harness lines. | Recorded as Q23 with the flip criterion; ADR-0005 stands. |
| F8 | **M5's metric had no denominator rule.** | Acceptance "first 10 executions … regression visible" against §2.5's "≥ 30 labelled executions"; labels depend on the task mix. | Decided: ADR-0028 — `n` and the `unknown` share from the first label, a comparison only from 30 per revision. |
| F9 | **Hermes injects a nested file whole into a tool result, with a ceiling.** | `agent/subdirectory_hints.py`: first match per directory, 32 KiB ceiling, "~8k" recommended; also verified there: `.hermes.md` nearest-up precedence, `.agents/skills` behind `trusted_project_dirs`, shell hooks with `hook_event_name` on stdin, wiring in `~/.hermes/config.yaml`. Not found: a `version` requirement in the skill loader. | Built: ADR-0029, C7 budgets 8 KiB nested / 32 KiB root; fires on a 9.9 KB nested file in the corpus. M3h's `version: 1` is to be verified before it is built. |
| F10 | **State schema tolerance was only manually verified.** | §8.2 left it; no test for a foreign `schema_version`. | Built: `test_status_names_adopt_on_a_foreign_state_schema`. |
| F11 | **`--json` existed for `check` only.** | `status`, `doctor` printed prose for CI to parse. | Built: `status --json`, `doctor --json`, same exit codes. |

### 10.2 What holds

- Suite 296 → 305 tests, 98 %, 11 s on Linux; `ruff` clean; goldens changed by exactly one line (`root_share` in
  the poly plan header), on purpose.
- Determinism per rev: `as_of` is the trunk rev's committer date, so a re-plan differs only where the rev did.
- The upgrade path: a v3 model on disk → `plan` rebuilds it; a foreign state → `status` names `adopt`.
- Never overwrite on the corpus: a hand-written nested `AGENTS.md` gets its block appended, the root file
  untouched; `check` 0 FAIL on all four repositories before and after M3e.
- Speed on the corpus (54 files → 20.6k files, 1 → 122 modules): scan 0.6 / 1.7 / 3.5 / 6.4 s — the slowest
  repository carries 22.4k non-merge commits in 90 days and 1 839 authors, and the rank rule still yields four
  agents at ranks 1–4; plan ≤ 1 s; `doctor --offline` "ready" on all four.
- ADR-0023's premises about Hermes hold in its source (F9), with one correction for M3h.

### 10.4 Addendum — an external review of v0.7.0 (2026-09-17)

| # | Finding | Evidence | Consequence |
|---|---|---|---|
| F12 | **`apply` wrote bytes computed from the preview's read; a file that moved during `apply? [y/N]` was overwritten, prose outside the markers included.** | `cli.py`: `plan_files` before `input()`, `write()` after it without re-reading; `_replace_blocks(current, …)` on the stale `current`; the rollback restored the same stale read; the checker sees structure, not lost content. Reproduced with a test before the fix. | Built as M3f: compare-and-swap in `write()` (ADR-0030) — `changed since the preview (skipped)`, record kept, listed after the checker summary. Not built: a lock file (Terraform's answer to two concurrent runs); the comparison covers the second run's writes, a lock becomes a question with the runtime direction (§0). |
| F13 | **`apply` wrote through symlinks: an `AGENTS.md` linked to a file outside the repository received the block there; inside, `AGENTS.md → CLAUDE.md` would put two records on one file.** | `Path.write_text` and `mkdir` follow links; no check anywhere. | Built as M3f: any symlink in a target path → `symlink in the path — never written through (skipped)` in the preview, as `git apply` refuses paths through links (ADR-0031); the write phase checks again. |
| F14 | **A write error half-way left a torn harness: earlier files written, the failing one truncated, the state untouched; rollback only on new checker FAILs.** | `write()` used `Path.write_text` (truncate, then write) and caught nothing; simulated `OSError` on the second of two files. | Built as M3f: harness files go through `sherpa.atomic` like the index files, an `OSError` rolls back what was written, a failed rollback names the paths and the way out (ADR-0032). Not built: a cross-file journal — Git already restores what a crash between two renames leaves. |
| F15 | **`adopt` lifted the hand-edit guard on base files: a hand-edited hook was `! hand-edited` before a state rebuild and `~ updated` (overwritten) after it.** | ADR-0017 §2 "base files are sherpa's by name"; `adopt._reconcile` recorded the on-disk hash as `generated`. | Built as M3f: a differing base file is `adopted` (yours) with a gap line naming the refresh (delete, `apply`) — `terraform import` semantics; ADR-0033 amends ADR-0017 §2. |
| F16 | **A torn state plus a moved trunk was a recovery dead end: `plan` failed on the state ("run `sherpa adopt`"), `adopt` failed on the stale plan ("run `sherpa plan`"), both exit 1 — and a torn state alone stopped `plan` and `status`.** | `cli.py`: `mark_covered(plan, _load_state(repo))` without a fallback in `plan`; `_refuse_stale` before the state fallback in `adopt`; `_load_state` bare in `status`. Reproduced with a test before the fix. | Built: `adopt` does not check staleness (`terraform import` needs the resource, not a fresh plan); `plan`, `status`, `adopt` treat a torn state as empty with the message on stderr; only `apply` refuses both (ADR-0034, amends 0017/0019). |
| F17 | **`self-update` never worked end to end: the wheel was saved as `sherpa_harness.whl` (pip: `is not a valid wheel filename`), and without a token the private API's 404 was raised before the git fallback — `doctor` and the hint failed the same way.** | `update.py`: `download` named the file after the asset's API URL (a number); `latest_release` raised on 404 without a token, `self_update` never reached `git+…@tag`. Reproduced with a real download and `pip install --dry-run`. | Built: `Release.wheel_name` from the asset, validated against PEP 427 before pip sees it; without a token `git ls-remote --tags` (https, then ssh, never prompting) finds the newest `v*` tag (ADR-0035, amends 0018 §2). Bar: pip's own answer on a wheel the code downloaded, not a mocked installer. |
| F18 | **A production install validated nothing: `jsonschema` is a dev extra, `validate()` a no-op without it. `decision: rejcet` passed `plan_from_dict`, `selected()` read it as not rejected and rendered the refused agent; `schema_version: 999` and `kind: wizard` passed too.** | `yamlio.validate`, `state.validate`, `model.validate`: `except ImportError: return`. Reproduced with `sys.modules['jsonschema'] = None`. | Built: `sherpa/schema.py`, a stdlib interpreter for the keyword subset the schemas use, on every reader; `jsonschema` stays the dev reference and `tests/test_schema.py` runs one matrix through both (ADR-0036, amends 0005). |
| F19 | **Non-ASCII paths lost their churn.** `git log --name-only` C-quotes `über.py` as `"\303\274ber.py"` without `-z`; `ls-tree -z` does not; `collect()` dropped the quoted name. Hotspots, authors and module churn wrong for every repository with such a path. | `t0_git.log_since`: no `-z`; reproduced with `normal.py → 1, über.py → 0`. A newline path would also have shifted every `cat-file --batch` answer after it. | Built: `-z` in `log`, NUL parsing; newline paths get no LOC instead of being sent (ADR-0038). Test with umlaut, CJK, tab and newline. |
| F20 | **Coupling counter and printed denominator did not match.** `share = shared / measured commits`, the row said `6 of 15 commits, 50 %` with `commits_90d` — 6/15 is 40 %. | `t1_modules.compute_coupling` vs `render.coupling_row`. | Built: `Coupling.of` in the model (schema v5), row `6 of 12 measured commits, 50 %` (ADR-0039); `status`/`apply` name `sherpa plan` for an older model. |
| F21 | **Outcome labels held false successes and wrong revisions.** `cat pytest.ini` matched `TEST_RE` → `tests_run=1`, exit 0 → `success`; `harness_rev` read at Stop, so an `apply` inside the execution rebooked the label. | `sherpa-outcome.py` `TEST_RE` (substring), `stop()`; reproduced. | Built: `is_test_run` — runner as command word per shell segment, wrappers and paths stripped; `harness_rev` at start, `harness_rev_at_stop` when it moved; 30-case classifier matrix in the tests (ADR-0040). M5 leaves records with `harness_rev_at_stop` out. |
| F18 | **A preview failed on configuration: with `.agents/` and `.claude/` both present and nothing decided, `apply --dry-run`, `adopt --dry-run` and `status` stopped with "set `[apply] home`" before listing a file.** | `cli._resolve_layout` raised for every `ask=False` call; first run on a large repository with a hand-written `.agents/` and a cloned `.claude/`: one line of output. | Built: a preview assumes `.agents` (the same default an interactive Enter takes) and prints the assumption after the `targets:` line; `--yes` and a terminal-less write still refuse; no flag — a layout stays a decision (ADR-0036, amends 0015 for read-only runs). |
| F19 | **A `.claude/` that is a repository of its own (a harness kept in a separate clone, `.claude/.git`) received 141 files without a word — tracked by the clone or by nobody, never by the repository `apply` ran in.** | Same run; `_resolve_layout` never looked for `.git` under the home or `.claude/`. | Built: one note per directory (`note: .claude/ is a repository of its own (.claude/.git) — files written there are not tracked by this repository.`) in the dry run, the write and `adopt`; a note, not a refusal (ADR-0037). |

### 10.3 Innovation candidates confirmed

1. **Change coupling as a harness fact** — quotable now that the catch-all is out (F3); the next proof is a
   golden on a fixture with a root bucket showing the partner row without it.
2. **One outcome table across two runtimes per `harness_rev`** (M3h + ADR-0028): nobody measures whether the
   same harness helps Claude Code and Hermes users differently; the hook already accepts both payload shapes.
3. **Stale-plan awareness with zero churn** (F1 + F7): `plan: stale` next to `drift: none` is Terraform's
   "no changes" for documentation, one level up.
