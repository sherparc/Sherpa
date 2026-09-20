# Sherpa — Plan

> **Created:** 2026-09-16 · **Revised:** 2026-09-20 (revision 37: the review at v0.8.2 (§14) and its first slice M3l — `harness_rev` over what an agent reads and `tooling` apart, so an upgrade no longer starts a revision (ADR-0056, Q36 decided), C7's budget for seeded files and the ceiling for the team's (F59), git-ignored files outside the checker (F62), the state validated on read (F66), a foreign `hooks` shape skipped instead of a traceback (F60), `status` capped to the recent revisions (F65), the README counts (F61); Q28, Q29/F63, Q37 decided with their slices, F28 struck, F29 with M5; the corpus of record is two repositories and Sherpa's own harness is no test subject; theses E10–E12; 451 tests, 98 %; revision 36: M3j second slice, the fruit of §13 without a decision — a dropped decision is named once (F42), a decision follows a unit whose manifest name changes and whose path stays (F55), the uninstall's reporting moves from `cli.py` into `apply` (F43) and names the state once (F53), the post-write check measures drift against the state the run wrote so `apply` and `check` print the same WARN count (F52), the troubleshooting row for an older harness (F46), F44 and F47 verified done; theses E06 to E09; Q38 struck, Q35 and Q36 still open; 449 tests, 98 %; revision 35: version 0.8.2 — #41 to #45, the own-unit rename, the e2e follow-ups of 0.8.1, the theses as code (ADR-0055) and F57, so a PyPI install carries them; the version lives in one place from here, `src/sherpa/__init__.py`, and `pyproject.toml` reads it (ADR-0018 §1 amended); revision 34: the first e2e job on Windows `main` found F57 — `apply` without `--yes` asked on a redirected `NUL` and died on EOF; one `_ask` for both questions treats EOF as no terminal, closed with its fixture, 443 tests; the e2e skill's run block becomes prose; revision 33: the end-to-end theses become code (ADR-0055) — `tests/e2e/`, one pytest per claim of README, CLAUDE.md and the ADRs against the `sherpa` command, the evidence line recorded and printed as the theses table, lifecycle phases that block instead of failing twice, a built-in monorepo for CI (`e2e` job on the ADR-0043 matrix) and the local corpus repository through `SHERPA_E2E_REPO`; five follow-up theses join the 22 of the skill (the deployed checker under `python -I -S`, the write boundary of `apply`, the configured home, CRLF kept, a dangling symlink as a finding); the skill becomes the procedure; §5 gains the row; revision 32: the e2e run on 0.8.1 — 21 of 22 theses hold on the 122-module corpus repository, the release focus (PyPI as `sherparc`, `self-update` reading the index) confirmed; F56 closed (`status` says which home it assumes, ADR-0036's third preview) and its six open items built — the rollback line on stderr, `doctor`'s runtime line names the targets and hints when Claude Code is not one, exit code 2 documented, the e2e skill's grep, the apply header counts selected entries, decision-address errors name the kinds and cap the list; 442 tests; revision 31: the own harness unit renamed `sherpa-harness` → `sherparc` through the normal path after ADR-0054 merged, which showed F55 — a kept decision is keyed by the target name and does not follow a renamed unit; the demo card re-rendered and its path normalisation made Windows-proof; revision 30: the PyPI package is `sherparc` (ADR-0054, amends ADR-0009 and ADR-0053) — `uv tool install sherparc`, `sherpa-harness` 0.8.0 stays on the index untouched, version 0.8.1; revision 29: PyPI is the index (ADR-0053, takes ADR-0018 §5) — `release.yml` publishes through trusted publishing after the GitHub release and refuses a version the index has, `self-update` and `doctor` read PyPI first without a token and the installer fetches the wheel itself, the README installs with `uv tool install sherpa-harness`; version 0.8.0; revision 28: the contribution path of M2c — DCO sign-off on every commit checked by an own `dco.yml`, Contributor Covenant 2.1, a security policy naming the write surface, issue and pull request templates (ADR-0052, takes ADR-0010 §4); revision 27: the launch slice M2c opened — the licence flipped to PolyForm Small Business or Noncommercial at the user's option (ADR-0051, the second stage of ADR-0010; the repository had been public since its creation), the docs stop calling the repository private, PyPI, `CONTRIBUTING.md` with a DCO and a README demo recorded as the rest of the slice, Q39 asks whether M3k moves ahead of M3h for the announcement; revision 26: the e2e run on 0.7.9 — 22 of 22 theses hold on the 122-module corpus repository, F49 and F50 confirmed closed; its side-findings F51 (a dangling symlink crashed the checker — a C4 finding now), F52, F53 recorded and F54 (the skill's own drift) closed; the e2e run joins every tag release and every e2e finding names its fixture; revision 25: the first end-to-end run on the 122-module corpus repository could not write — a root-level manifest rendered a `../` too many into the root `AGENTS.md` (F49) and the rollback left empty homes behind that made the next run ask (F50); both closed, ADR-0032 amended, a root-manifest fixture, version 0.7.9; revision 24: host breadth as a milestone — M3k, one thin adapter per runtime for Codex, OpenCode, Copilot, Cursor and Gemini CLI right after M3h (ADR-0050, Q8's corpus gate dropped), prompted by the comparison with metaharness in §9.1; the README states the difference in one sentence and names the neighbour under `## Related`; revision 23: the code review of M3j's first cut before it merged — the cover by path is decided by `plan` from the files and reported by `adopt`, a file with prose of its own outside sherpa's markers is the team's doc before and after `apply` appended its block, so the second `adopt` and a lost `.sherpa/` see the same cover, one `mark_covered` with one precedence, the open-owner-doc gap reads `covered:`, the claude-only row names the nested `CLAUDE.md`, and an older agent seed is modernised like an older stamp so the uninstall still takes the file back (ADR-0049 revised, amends ADR-0022); revision 22: M3j first slice — a nested `AGENTS.md` at a unit's own path covers its owner-doc entry by path, the plan's word beats the path, the path beats the heuristic, `apply` writes the facts block into the team's file and no skeleton (ADR-0049); the agent seed stops carrying the doc path; Q34 decided; revision 21: the whole-product review at v0.7.6 (§13) — a nested `AGENTS.md` at a unit's path is not an owner doc to Sherpa, the first-apply count measured at 243 on the 122-module corpus repository, `harness_rev` still moves with the version, F32 carried twice; Q34 to Q38, M3j proposed before M3h; revision 20: M3i second slice — `apply` takes its own bytes back and `apply --remove` is the uninstall, `adopt` records its leftovers as sherpa's (ADR-0048); Q26 decided, F24 and F25 closed, the M3i acceptance sharpened to `git status --ignored` unchanged after apply + remove; revision 19: M3i first slice — one repository: a nested repository anywhere in the tree stops `apply` and `adopt` (ADR-0045, supersedes 0037), `covered:` by hand is a decision and only `docs/modules/` links, one file per entry (ADR-0046), the checker fails only in generated files (ADR-0047); Q30 to Q32 decided, §12.4 measured; revision 18: the field test on a grown harness (§12) — a nested harness repository is invisible to `adopt`, hand-named owner docs stay unlinked, the checker fails on files sherpa never wrote, three files per module — F34 to F38, Q30 to Q33; CI definitions found by directory (ADR-0044); revision 17: the manager review (§11) — Sherpa creates and updates but cannot remove: a rejected entry or a vanished unit stays live in the runtime and a state rebuild adopts sherpa's own leftovers as yours, F24 to F33, Q26 to Q29, M3i proposed before M3h; revision 16: F20 to F23 closed — stdlib schema validation on every reader (ADR-0042), NUL-separated git paths (ADR-0038), the coupling denominator in the row (ADR-0039), test runs as command words and the start revision on outcome labels (ADR-0040); the mechanics drawn as Mermaid under `docs/architecture/` (ADR-0041, Q25) and the CI matrix by event (ADR-0043); revision 15: two findings from a first run on a large repository with two homes, F18/F19 — a preview never refuses (assumes `.agents` and says so, ADR-0036) and a target directory that is a repository of its own is named (ADR-0037); revision 14: F17 closed — `self-update` saves the wheel under its PEP 427 name and finds the tag with `git ls-remote` without a token, verified with pip itself, ADR-0035; revision 13: the review's F16 closed — `adopt` no longer refuses a stale plan and `plan`/`status`/`adopt` run on a torn state, ADR-0034, so a broken index plus a moved trunk has a way out; revision 12: an external review of v0.7.0 found the write path overwriting a file that moved between the preview and the confirmation — writing through symlinks, a torn harness after a write error, and `adopt` lifting the hand-edit guard on base files — closed as M3f with compare-and-swap, a symlink guard, atomic writes with rollback and base files as yours, ADR-0030 to 0033, §10.4) · **Author:** Claude (Opus 5) with Andrei
> **Status:** v0.8.2 — M0, M1, M1a, M2, M2b, M3a, M3t, M3c, M3d, M3e, M3f, M3i (two slices: see what exists, take back what is sherpa's), M3j (first slice: the cover by path; second slice: the §13 fruit F42–F47, F52, F53, F55), M3l (a revision that means something, §14) done, M2c (the launch slice) opened with the licence; order from here: M3m (the CI contract: `status --exit-code`, `apply --dry-run --json`, Q29/F63) → M2c's changelog and announcement → M3h (with Q28) → Q37 → M3k → M5 (with F29) → M7a → M6-lite → M4 → M6 → M3b → M7 (§7.3, §9, §9.1, §10, §13, §14)
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
front of its users with a day of work; Codex, OpenCode, Copilot, Cursor and Gemini CLI follow as adapters of
their own right after it (M3k, ADR-0050: host breadth is a goal, one thin adapter per runtime — detection, the
host's native rule file, its hook — no longer gated on a corpus repository using the host), and Sherpa itself is
installed **inside** those runtimes as a thin plugin or bundle (M7a, ADR-0024) — one command where the user
already works. Second, the **provider layer** (M6-lite, ADR-0004: thin, framework-free — bring your own key, local models
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
- **Never overwrite, only add — and take back only its own** (ADR-0016, ADR-0048): in the user's repo `apply`
  creates, appends and merges; it rewrites and removes only its own unchanged bytes (hash in the state), and
  `apply --remove` is the uninstall that leaves a clean repository clean.
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
asset); `release.yml` builds the wheel `sherparc` (ADR-0054) from it on every tag `v<version>`, installs it into a
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
| M2b ✅ | distribution + onboarding: `sherpa doctor`, `release.yml` (tag → wheel → GitHub release), `sherpa self-update`, daily update hint (`SHERPA_NO_UPDATE_CHECK`), GitHub Releases as the index (ADR-0018) | `doctor`: nine checks with a fix each (eleven since ADR-0045), exit 1 only on a fail; `self-update` through the owning installer (uv/pipx/pip), git-tag fallback without a token via `git ls-remote` and the wheel under its PEP 427 name (ADR-0035, F17), clones refused; the hint is a background thread plus cache — zero wait; 282 tests, 98 % |
| M3d ✅ | low-hanging fruit from the retro (§7) plus the two preconditions the review found (§8): stamp without rev (ADR-0019) with legacy-stamp recognition in `adopt` (ADR-0022), model v4 with `sub_dirs` and sub-units by the depth rule (ADR-0020), change coupling with a size cap (ADR-0021), `plan --accept/--reject` by address, root index capped at 20 by rank, privacy note for the hook, session-built fixtures | `test_trunk_move_without_activity_changes_no_block`: two revs, no activity → `nothing to do.`; `test_adopt_recognises_an_older_stamp…`: 0.5.0 bytes → lost state → adopt → apply → `nothing to do.`; Sherpa's own plan lists `src/sherpa/apply`, `plan`, `scan` as units; `test_root_index_is_capped_and_ordered_by_rank`; suite 12 s → 7 s on Linux; 296 tests, 98 % |
| M3e ✅ | fruit of the whole-product review (§10): `status` names a stale plan and has `--json`, `doctor --json`; two manifests in one directory decided by language share (ADR-0025, closes Q4); coupling without the root catch-all (ADR-0026); the depth rule on a dominant root module (ADR-0027); proximity-file budgets in C7 (ADR-0029); the M5 denominator decided (ADR-0028); the architect agent's stale facts removed | `test_status_reports_a_stale_plan_and_json`; `test_find_modules_two_manifests_the_language_with_more_files_wins`; `test_coupling_excludes_the_root_catch_all`; `test_sub_units_for_a_root_module_only_when_alone_or_dominant`; `test_c7_proximity_file_budgets_in_bytes`; `test_status_names_adopt_on_a_foreign_state_schema`; corpus: the polyglot root is `python` now, coupling rows 21 → 11 and 15 → 13, 9 sub-units on the dominant root, C7 fires on a 9.9 KB nested file; 305 tests, 98 % |
| M3f ✅ | write safety: `apply` never overwrites a file that changed between the preview and the write — `write()` re-reads and compares with the preview's read, skips with `changed since the preview` and keeps the record, a rollback touches only what was written (ADR-0030); a path with a symlink in it is never written through, in or out of the repository (ADR-0031); every file is written whole or not at all and an `OSError` half-way rolls back what was written (ADR-0032); `adopt` records a differing base file as yours instead of sherpa's by name (ADR-0033, amends 0017 §2; §10.4); `adopt` ignores a stale plan and `plan`, `status`, `adopt` run on a torn state with the way out on stderr — only `apply` refuses both (ADR-0034, F16); a preview (`apply --dry-run`, `adopt --dry-run`, `status`) with two homes and nothing decided assumes `.agents` and says so instead of refusing, a write still asks or refuses (ADR-0036, F18); a home or `.claude/` that is a repository of its own is named with one note, never refused (ADR-0037, F19) | `test_write_skips_a_file_that_changed_since_the_preview` (managed, blocks, hooks; prose outside the markers survives), `test_write_skips_a_file_that_appeared_since_the_preview`, `test_rollback_never_touches_a_file_skipped_since_the_preview`, `test_plan_never_writes_through_a_symlink`, `test_plan_never_writes_through_a_symlink_to_a_sibling`, `test_write_skips_a_path_that_became_a_symlink_since_the_preview`, `test_write_rolls_back_when_a_write_fails_half_way`, `test_write_names_what_a_failed_rollback_left_behind`, `test_write_is_atomic_per_file`, `test_adopt_keeps_hand_edits_in_blocks_and_in_base_files`, `test_adopt_and_plan_run_on_a_torn_state_after_the_trunk_moved`, `test_resolve_layout_preview_assumes_agents_when_both_homes_exist`, `test_cli_dry_run_assumes_a_home_and_the_write_refuses_without_a_terminal`, `test_resolve_layout_names_a_target_directory_that_is_a_repository_of_its_own`, `test_cli_apply_names_a_nested_repository_in_the_dry_run_and_the_write`; 326 tests, 98 % |
| M3i ✅ | the manager sees what exists and takes back what is sherpa's (§12, §11 F24/F25). Slice 1: one repository — a nested repository anywhere in the tree stops `apply` and `adopt`, the dry runs note it, `doctor` says it first with `repositories` and names an undecided home with `layout` (ADR-0045, supersedes 0037); `covered:` by hand is a decision, only `docs/modules/` links, one file per entry, ties cover nothing (ADR-0046); C1–C5 FAIL only in generated files, `check --strict` (ADR-0047). Slice 2: `apply` removes a rejected entry's or a vanished unit's files, blocks and hook groups when the bytes are still sherpa's, hands back hand-edited ones as `yours now`; `apply --remove` is the uninstall, index and telemetry included; a seeded blocks file remembers it was sherpa's whole; `adopt` records its leftovers as generated, never as covers (ADR-0048). Open, moved to the next slice: F26 content-only `harness_rev` (Q27), F32 dropped decisions named, F27/F28/F29/F30/F31, F37 (Q33). | **acceptance:** `apply` + `apply --remove` on a clean repository leave `git status --ignored` exactly as it was, merged JSON keys, appended blocks, index and telemetry included — measured on a clean clone of Sherpa itself: 10 written, 10 removed, identical; the three §11 lifecycle experiments are tests (`tests/test_remove.py`): reject after apply, unit gone from the trunk, uninstall with and without hand edits, the F25 rebuild; on the §12 repository `doctor` names the nested clone and `apply`/`adopt` refuse |
| M3j | owner docs where the team already writes them (§13 F39). Slice 1 ✅: a nested `AGENTS.md` at a unit's own path, with prose of its own outside sherpa's markers, covers its `owner-doc`/`test-infra` entry by path — exact, no heuristic; `plan` sets the cover from the files and `adopt` reports it, so `plan → apply` needs no `adopt` and a lost `.sherpa/` finds the cover again; precedence `covered:`/`decision:` > path > name/mention link, in one function; the covering file stays unrecorded so `apply` appends its facts block (with the `claude` target only, the nested `CLAUDE.md` carries the facts), and no `docs/modules/` skeleton is rendered for a covered unit; the proximity block drops a pointer that would target the file itself; the agent seed stops carrying the doc path in static prose, and an older seed is modernised like an older stamp (ADR-0049). Slice 2 ✅ (the fruit of §13 that needs no decision, 2026-09-19): a decision whose entry left the plan is dropped with one line (`agent:pay:svc/pay [reject] is no longer in the plan — dropped`, F42) and follows a unit whose manifest name changes and whose path stays — one decided entry of that kind and scope left, one new one arrived — said once (`followed from … (same path, renamed)`, F55); `write(remove=True)` fills `Result.yours/uninstalled/stray/records_kept` and `render_result` prints the uninstall's four lines, `cmd_apply` composes nothing (F43) and the state is named once, in the `uninstalled —` line (F53); the state is written before the post-write check and a rollback restores the previous one, so `apply`'s WARN count is `check`'s (F52); the troubleshooting row for a harness older than 0.7.6 (F46); F44 and F47 were already done on 0.8.2. Still open, each a decision: Q35/Q33 (kind counts, proximity `CLAUDE.md` opt-in), Q36/Q27 (content-only `harness_rev`), Q37. | the five-module fixture with a hand-written `svc/pay/AGENTS.md`: `plan` reports `1 covered by existing files`, `apply` straight after it writes the facts block into the team's file and no skeleton, the agent's manifest points at it, the second run is all `=`; `adopt` covers `owner-doc pay` (row: `covers owner-doc pay (the unit's own path)`) and the second `adopt`, the one after `apply`, and the one after `rm -rf .sherpa` + `plan` print the same rows and gaps and record the same state (no `hand edit`, no open owner doc for pay); a hand `covered:` on an applied unit takes the skeleton back (`- removed (no longer in the plan)`), `check` 0 FAIL; a hand-written `covered:` beats the path, the path beats the link (loser named, no gap), root `AGENTS.md`/nested `CLAUDE.md`/block-only/ignored files never cover; with the `claude` target only the row says `the facts go to svc/pay/CLAUDE.md` and the nested `CLAUDE.md` carries them; an agent seeded by 0.7.7 is `sherpa's, an older seed — apply refreshes it` after a state rebuild, `apply` says `seed refreshed`, `apply --remove` deletes it; golden `active-adopt-bypath-console.txt`; corpus: the 16-module repository with 12 nested `AGENTS.md` — 9 covers, open owner docs 22 → 13, `apply --dry-run` 38 → 29 to add; the other three corpus repositories: 0 covers, no false positives; 423 tests, 97 %. Slice 2: `test_merge_decisions_names_a_dropped_decision_once_and_writes_it_to_no_entry`, `test_merge_decisions_follows_a_renamed_unit_and_stops_at_an_ambiguity`, `test_cli_plan_keeps_a_rejection_across_a_renamed_manifest` (a single-manifest fixture whose `name` changes on the trunk), `test_the_uninstall_is_reported_by_apply_not_composed_by_the_cli`, `test_remove_keeps_the_index_while_a_record_of_sherpas_stays`, `test_apply_warn_count_equals_check_right_after` (red on 0.8.2: `4 WARN` from `apply`, `0` from `check`); theses E06–E09 on the built-in corpus and the local one; 449 tests, 98 % |
| M3l ✅ | a revision that means something (§14, ADR-0056): `harness_rev` is the hash over the content records — the markdown an agent reads — and `tooling` the hash over the checker copy, hook, wiring, ignore file and the sherpa version, so a `self-update` plus `apply` keeps the revision the outcome labels are grouped by (Q36); the state is validated against its schema on every read and tolerates unknown top-level keys (F66); C7's 8 KiB budget for proximity files sherpa seeded, the 32 KiB ceiling for the team's (F59); a file git ignores is not checked (F62); a `settings.json` whose `hooks` is somebody's shape is skipped with a line (F60); `status` shows the current revision plus the five most recent and counts the rest (F65); README counts from the collector (F61) | `test_harness_rev_changes_only_with_content_and_tooling_with_the_version`, `test_c7_soft_budget_only_for_files_sherpa_seeded`, `test_git_ignored_files_are_not_the_harness`, `test_state_load_names_the_way_out` (a record no sherpa wrote is refused with its location), `test_hooks_merge_keeps_foreign_entries` (three foreign shapes skipped); theses E10–E12; the 16-module corpus repository with 12 hand-written nested `AGENTS.md`: `check` 8 WARN → 0, `apply --yes` 9 WARN → 0, round trip clean; the empty harness is `e3b0c44298fc` for every version; 451 tests, 98 % |
| M2c | public release (ADR-0051, the second stage of ADR-0010). Done ✅: the licence is PolyForm Small Business 1.0.0 or PolyForm Noncommercial 1.0.0 at the user's option — free for individuals, noncommercial organisations and companies under the Small Business limits, a commercial licence above; both texts in `LICENSE`, the SPDX expression in `pyproject.toml`, the output exception kept; the docs stop explaining the token by a private repository. Done ✅ (ADR-0052): `CONTRIBUTING.md` with the DCO sign-off, `dco.yml` refusing a pull request with an unsigned commit (its own workflow, so docs-only pull requests are checked too), `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), `SECURITY.md` naming the write surface and the private channel, issue and pull request templates. Done ✅ (ADR-0053): `release.yml` publishes wheel and sdist to PyPI on every tag through trusted publishing after the GitHub release and refuses a version the index has; `self-update` and `doctor` read PyPI first without a token, the installer fetches the wheel itself (`sherpa-harness==<version>`), GitHub Releases and `git ls-remote` stay the fallback; the README quick start is `uv tool install sherparc` (the project renamed from `sherpa-harness` an hour after 0.8.0, ADR-0054); version 0.8.1. Observed on the rename of the own unit (`sherpa plan .` after the merge, ADR-0054 §4): the owner doc and the librarian skill moved as ADR-0048 promises, but the kept decision `agent sherpa-harness [reject]` did not — the decision key is `kind:target:scope` and the target is the manifest name, so a renamed unit at the same path starts without its decisions and the rejected agent was proposed again (re-rejected by hand). **F55, open**: a decision should follow a unit whose path stays and whose name changes; the fixture that catches it is a single-manifest repository whose manifest `name` changes between two plans. The demo at the top of the README is the real `sherpa plan .` on this repository, rendered as an SVG card by `scripts/render-demo.py` (stdlib, deterministic, the home directory normalised away) and refreshed with every release — Sherpa on itself, so no public repository has to be named; 442 tests. Open: a `CHANGELOG.md` generated from the release notes. Then the announcement. | `pip download sherparc` gets the wheel of the tagged version with `License-Expression: PolyForm-Small-Business-1.0.0 OR PolyForm-Noncommercial-1.0.0`; `sherpa self-update --check` on a machine without a token and without git credentials reports the current version from PyPI; `release.yml` refuses a tag whose version is already on the index; the e2e run on the tagged `main` holds; `CONTRIBUTING.md` links from the README and the `dco` check fails a pull request with an unsigned commit (verified against a pull request before the rule and one after it); the README's first screen shows the demo card and the one-line install, and `python3 scripts/render-demo.py` renders the same bytes twice from the same output |
| M3h | `hermes` target (ADR-0023): third entry of `TARGETS`, detected by `hermes` on the `PATH`, `~/.hermes/` or `.hermes.md`; thin on top of `agents-md` — appends the root block to `.hermes.md`/`HERMES.md` when it exists (first match wins there), `version: 1` in every skill's front matter (neutral core), one outcome hook script for both payload shapes (`PostToolUse`/`Stop` and `post_tool_call`/`on_session_end`), `apply` prints the `~/.hermes/config.yaml` hook snippet once, `doctor` checks `hermes-hook` and `hermes-trust` (`hermes skills trust`), `status` counts labels from both runtimes per `harness_rev` | five-module fixture with targets `claude, agents-md, hermes`: same files as before plus `version:` (goldens on purpose), a fixture with `.hermes.md` gets the block appended and `AGENTS.md` untouched; hook test with a Hermes payload → label with the same `harness_rev`; `doctor` on a machine without Hermes: no new line; corpus: `hermes` launched in one repo loads the nested `AGENTS.md` and lists the skills after `trust`; C7 (ADR-0029) fires on the corpus repository with an oversized nested file. Verified in Hermes' source (§10): the skill loader does not require `version` in the front matter — keep `version: 1` only if the skills hub needs it, verify before building |
| M3k | host adapters (ADR-0050): `codex`, `opencode`, `copilot`, `cursor`, `gemini` as further entries of `TARGETS`, each thin on top of `agents-md` exactly like `hermes` — a `doctor` line when the host's marker is present (`.codex/`, `.opencode/`, `.github/copilot-instructions.md`, `.cursor/`, `.gemini/` or `GEMINI.md`, the binary on the `PATH`) and the default target set following the detection; the host's native rule file only where it carries something `AGENTS.md` cannot (Cursor `.cursor/rules/*.mdc` with `globs`, Copilot `.github/instructions/*.instructions.md` with `applyTo`, `GEMINI.md` when the host does not read `AGENTS.md`) as a managed file or block that imports or repeats the proximity facts; the outcome hook where the host has a JSON-on-stdin hook contract, one script for every payload shape; a host that reads `AGENTS.md` and `.agents/skills` and has nothing of its own gets no adapter and is named by `doctor` as covered. Each adapter starts with a dated contract note under `docs/concepts/hosts/`, verified against the host's documentation or source | five-module fixture with every target on: the `agents-md` files unchanged byte for byte (goldens), one native file or block per host that has one, second run all `=`; `doctor` on a machine with none of the hosts: no new line, with a marker present: one line naming the host and what it reads; hook test with each host's payload → a label with the same `harness_rev`; corpus: one repository launched in Codex, OpenCode and Cursor loads the nested `AGENTS.md`/rule file at a unit's path (recorded in the contract notes); `apply --remove` takes every native file back |
| M5 | outcome evaluation (ADR-0028): `status` shows labels per `harness_rev` with `n` and the share of `unknown` (records with `harness_rev_at_stop` left out, ADR-0040); a comparison between two revisions only from `outcome_min_n` (30) labelled executions each; Q14's fruit (test and build commands per unit, a `status` line for adopted files changed since adopt) | first 10 executions on a corpus repo with a label ≠ `unknown`; the `unknown` share visible from the first label; the comparison line appears at 30 per revision and names the missing count below; `status --json` carries the counts |
| M7a | runtime plugins (ADR-0024): a Claude Code plugin (`.claude-plugin/`, marketplace) and a Hermes bundle (`hermes bundles`, tap) generated from one source under `plugins/`, released with every tag; commands `/sherpa-doctor`, `/sherpa-plan` (reads the plan entry by entry, asks, writes the answer with `--accept/--reject`), `/sherpa-apply` (dry run shown, then `--yes` after the user's yes), `/sherpa-status`; thin — the CLI does the work, no hook in the plugin | plugin manifests validated in a test; `claude plugin install` from the release and `/sherpa-plan` on the five-module fixture ends with the same `harness-plan.yaml` as the CLI with `--accept/--reject`; Hermes: `hermes skills install` of the bundle lists the four commands; a missing CLI produces the install line, nothing else |
| M6-lite | provider layer (ADR-0004): thin, framework-free — bring your own key, local models through the OpenAI API (vLLM, Ollama, OpenRouter), Anthropic natively; no LangChain, no agent framework; used by M4 evals and M6 first | the same schema pass through a local OpenAI-compatible model and through Anthropic; a missing key produces one line and the stage-1 plan unchanged |
| M4 | auto-evals from the graph, `status` with baseline | eval run on the fixture ≥ 90 %; regression is reported |
| M6 | `plan` stage 2: LLM enrichment on top of M6-lite — comments only, stage-1 entries never change | plan diff stage 1 vs. 2 documented; the same schema pass with both providers; stage-1 entries unchanged |
| M3b | adapters `dotnet` + `python` (T2: anchors, patterns) — **proposed after M6-lite** (§7.3) | a scan yields the anchors a harness checker verifies today; owner docs get anchors |
| M7 | librarians, multi-repo (`/sherpa-plan` moved to M7a) | a second repo in the workspace |

Every milestone ends with: CI green (`.github/workflows/ci.yml`: pytest on Linux for pull requests, Linux and
Windows on `main`, macOS weekly, all three on a manual run — ADR-0043; coverage ≥ 90 %, ruff), docs updated (`plan.md`, the concept doc in `docs/concepts/`, the command reference in `docs/commands/`,
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
| End-to-end | the claims of README, CLAUDE.md and the ADRs against the `sherpa` command | `tests/e2e/` (ADR-0055): one pytest per thesis, the `sherpa` console script as a subprocess, the proving output line recorded and printed as a table; lifecycle phases as session fixtures that block the theses behind a failed one; the built-in monorepo in CI (`e2e` job, Linux per pull request, + Windows on `main`), the local corpus repository with `SHERPA_E2E_REPO` — verified clean before and after; not part of `pytest -q` |
| Corpus | two repositories of record cloned next to this one (never named): a 122-module Java monorepo and a 16-module Python repository with hand-written nested `AGENTS.md` (decided 2026-09-20) | the e2e suite on `SHERPA_E2E_REPO` and the round trip `apply --yes → status → apply --remove --yes` on both after every slice and before every tag release (`/e2e-test`); never in CI. Sherpa's own harness under `.claude/` is not a test subject — `sherpa status .` is the pre-commit smoke gate and nothing more; no number from it is evidence |
| Schema | `codebase-model`, `harness-plan`, `harness-state` | JSON Schema under `src/sherpa/schemas/`; the plan and the state are validated on every read and write by the stdlib validator `sherpa/schema.py` (ADR-0042, ADR-0056), the model on write — it trusts its own writer (ADR-0042 §consequences); `jsonschema` (dev extra) is the reference the tests compare it with on one input matrix |

Gate: coverage ≥ 90 % for `src/sherpa/`, `pytest -q` and `pytest tests/e2e -q` green before every milestone. Status: 451 tests, 98 %, 38 end-to-end theses. The test count in the README is read from the collector (`pytest --collect-only -q`) before it is written — thesis T22 checks it (§14 F61).
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
   are the next adapters once a corpus repo uses them. Gate dropped 2026-09-19 (ADR-0050): the adapters are M3k,
   right after M3h, gated on the host's documented contract instead.
9. ~~Interactive per-entry approval in the CLI was rejected for M3a (ADR-0013); `/sherpa-plan` in Claude Code (M7)
   is the better place. Reopen if the YAML editing turns out to be the friction point in customer tests.~~
   Decided 2026-09-17 (ADR-0024): the per-entry approval is the plugin's `/sherpa-plan` in M7a; the CLI keeps
   `--accept/--reject` for scripts and CI.
10. ~~Stamp without the rev (§7.1 G1)?~~ Decided 2026-09-17 (ADR-0019): the stamp is `as of <date>` only; the rev
    stays in the state and the plan header. Implemented in M3d.
11. ~~Sub-units for single-manifest repositories (§7.1 G2)?~~ Decided 2026-09-17 (ADR-0020): the depth rule, with
    `[plan] units = […]` in `sherpa.toml` as the override. Implemented in M3d.
12. ~~Milestone order (§7.3)?~~ Decided 2026-09-17: M2b → M3d → M5 → M6-lite → M4 → M6 → M3b → M7; revision 10
    inserted M3h and M7a before M5, revision 11 (§10 F6) put M5 back before M7a: M3h → M5 → M7a → …; revision 24 (ADR-0050) put the host
    adapters M3k between M3h and M5. Tree-sitter
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

26. ~~**Removal semantics (§11 F24, amends ADR-0016).**~~ Decided 2026-09-18 → ADR-0048, the recommendation: generated
    and unchanged bytes are taken back — a managed file by hash, a seeded blocks file whole while it is still the seed
    plus its blocks (a new whole-file hash on the record), else only the matching blocks, sherpa's hook groups by
    identity; a hand-edited file or block stays as `yours now`, the record is dropped; `apply --remove` does it for
    everything, index and telemetry included, and `adopt` records its own leftovers as generated (F25). Acceptance:
    apply + remove on a clean repository leave `git status --ignored` as it was. Before: Sherpa creates, appends and
    merges, and deletes nothing — so a rejected entry or a vanished unit leaves sherpa's own files live in every
    runtime, and `apply` says `nothing to do.`. Recommendation: remove only what is `generated` **and** unchanged
    (hash matches the state) with `- removed (no longer in the plan)` in the preview; a hand-edited file or block
    stays, its record is dropped and the line says `yours now`; in a nested `AGENTS.md` only the block goes, the file
    only when nothing but sherpa's block was in it. With "never delete, ever": F25 still needs the orphan record, and
    `status` must at least name `rm` as the way out — the rejected agent stays live until a human deletes it.
27. **`harness_rev` over agent-visible content only (§11 F26, amends ADR-0008/0028).** Today the hash carries the
    Sherpa version and the checker copy, so every `self-update` + `apply` starts a new revision without a doc,
    agent or block changing. Recommendation: yes, before M5 — docs, agents, skills and proximity blocks in
    `harness_rev`, the checker copy, hook, ignore file and version in a second field (`tooling`). With "no", M5
    must group by content anyway or its comparisons restart on every release.
28. ~~**Hook wiring in exec form, and which interpreter (§11 F27).**~~ Decided 2026-09-20 (§14): exec form with `python3` plus a `doctor` check `hook-python`, built with M3h and verified on the `main` Windows job. Claude Code runs shell-form hooks through
    PowerShell on Windows without Git Bash; the exec form (`command` + `args`) needs no shell but resolves one
    executable name on `PATH` — `python3` is missing on many Windows installs, `python` on many Linux ones.
    Recommendation: exec form with `python3` plus a `doctor` check `hook-python` that names the fix on the
    machine it runs on; alternative: keep `sh -c` and document "Git Bash required" — then Windows without it has
    no outcome channel, which contradicts ADR-0008.
29. ~~**`status --exit-code` (§11 F31).**~~ Decided 2026-09-20 (§14 F63): yes — exit 2 on drift or a stale plan, together with `apply --dry-run --json` as one "CI contract" ADR, the slice M3m right after M3l. Recommendation: yes — exit 2 on drift or a stale plan, as `terraform plan
    -detailed-exitcode` and `git diff --exit-code` do; it is the CI gate the milestone-step ritual already
    assumes ("status clean"). With "no", a gate needs `status --json` plus a JSON tool.
30. ~~**Which repository's ignore rules decide what is harness (§12 F34, amends ADR-0037).**~~ Decided 2026-09-17 →
    ADR-0045, the alternative: Sherpa works with one repository — a nested repository anywhere in the tree (a harness
    clone under `.claude/`, a submodule, a vendored clone) stops `apply` and `adopt` with the way out named; previews
    go on with a note. The first cut asked the nested repository itself and saw 1 111 files, half of them a knowledge
    vault inside the clone — whose files, whose ignore rules, whose harness are a second repository's questions, and
    Sherpa models one. Before: `adopt` drops git-ignored files ("personal files are not the harness") and asks the
    outer repository — so a `.claude/` that is a repository of its own and excluded there (`.git/info/exclude`, a
    common way to keep a nested clone out of the outer status) is dropped whole: 0 of its 51 files were seen, `apply`
    then wrote 39 owner docs and 11 agents next to the existing ones. Recommendation: for a directory ADR-0037 already
    recognises as a nested repository, ask **that** repository (`git -C .claude ls-files` decides; its own ignore
    rules apply), and `_nested_repositories` says so in its note. Alternative: treat a nested repository as fully
    foreign and refuse `apply` into it without `home` — then a team with a shared harness clone cannot use Sherpa at
    all.
31. ~~**The owner-doc link is a human decision, not a heuristic (§12 F35).**~~ Decided 2026-09-17 → ADR-0046:
    `covered:` by hand is kept like a decision and honoured first; only `docs/modules/` links; one file per entry,
    ties cover nothing and are named. No new field — `covered:` already is the field. Before: `adopt.link` matches by
    slug or by
    ≥ 2 unambiguous mentions of the unit path; on a harness that grew by hand it linked 22 of 51 files, put up
    to four files on one unit (analysis notes next to the owner doc) and left every abbreviated name (`kes.md`, `wsh.md`, `fev.md`) unlinked.
    Recommendation: a plan-side field `owner_doc: <path>` on the entry (and `agent: <path>`), set by the human
    or proposed by `adopt` with its reason, that `apply` honours instead of rendering a second doc — the
    Backstage `catalog-info.yaml` pattern: the team names the owner, the tool checks it. With "heuristic
    only": every abbreviation needs an alias table in `sherpa.toml`, which is the same decision in a worse
    place.
32. ~~**Checker scope on a grown harness (§12 F36).**~~ Decided 2026-09-17 → ADR-0047: FAIL only in generated files,
    WARN `(yours)` in adopted and unrecorded ones, `--strict` for all, strict without a state; `apply` counts what it
    writes as managed. Before: C4 walks every `.md` under both homes, so files sherpa never
    wrote — refinement notes, a vendored skill with broken relative links — fail `apply`'s post-check and
    `status` with 42 FAIL before the first sherpa file exists. Recommendation: FAIL for managed and adopted
    files, WARN for the rest (`C4 … (not managed)`), and `check --strict` for the old behaviour; the exit code
    then says something about sherpa's harness, not about the repository's history. Alternative: keep FAIL
    everywhere and let `apply` roll back only on **new** FAILs (it does) — then `status` stays red forever
    on such a repository and the team learns to ignore it.
33. **How many files may a first `apply` add (§12 F37).** 133 on a 48-module repository: the owner-doc floor
    (ADR-0014) accepts 39 units and each becomes three files under `claude` + `agents-md` (`.claude/docs/modules/x.md`,
    `x/AGENTS.md`, `x/CLAUDE.md` holding `@AGENTS.md`). Recommendation: keep the floor, but make the two
    proximity files one — `agents-md` writes `x/AGENTS.md`, the `claude` target adds the one-line `CLAUDE.md`
    only where the runtime is Claude Code **and** the team asked for it (`[apply] claude_proximity = true`),
    default off — and print the file count per kind in the dry run's last line so the team sees `39 owner
    docs · 11 agents · …` before it says yes. Alternative: a `--top N` on `plan` for owner docs — but a
    reasoned no per unit exists already, and a limit hides the reasoning.
34. ~~**A nested `AGENTS.md` at a unit's path is the owner doc (§13 F39, amends ADR-0046).**~~ Decided
    2026-09-18 → ADR-0049, built in M3j's first slice and revised after its code review (2026-09-19): the cover
    by path, set by `plan` from the files and reported by `adopt`; precedence `covered:`/`decision:` > path >
    heuristic; the team's doc is a file with prose of its own outside sherpa's markers — root `AGENTS.md`,
    nested `CLAUDE.md` and files that are nothing but sherpa's block never cover; the covering file stays
    unrecorded so `apply` appends its facts block; the agent seed stops carrying the doc path, older seeds are
    modernised. Before: the AGENTS.md convention makes the nearest file the one an agent reads; a team that
    keeps `gateway/AGENTS.md` has its owner doc there. `adopt` classed it `nested`, linked nothing, and `apply`
    wrote a skeleton `.agents/docs/modules/gateway.md` **and** appended the facts block into
    `gateway/AGENTS.md` — two owner docs, one empty.
35. **Q33 now, together with Q34 (§13 F40).** 243 files on the 122-module corpus repository, 229 of them owner-doc
    files for 77 entries (`docs/modules/x.md` + `x/AGENTS.md` + `x/CLAUDE.md`). Recommendation: as Q33 says —
    proximity `CLAUDE.md` opt-in, counts per kind on the dry run's last line — decided in the same PR as Q34,
    they are one table row.
36. ~~**Q27 before M5 (§13 F41)**~~ Decided 2026-09-20 → ADR-0056, built in M3l: `harness_rev` over the content records, `tooling` apart. Was — reaffirmed: after `--remove` every repository ends at the same `harness_rev`
    for one version and another for the next; the first outcome samples must not restart at 0.7.7.
37. **Q23 with the corpus number (§13 F45).** Decided 2026-09-20 (§14 F67): split — decisions and covers into a small checked-in file, the full plan ignored next to the model; a slice of its own after M3h, ADR then. Was: The busiest corpus repository has 24 215 commits in 90 days; the
    checked-in plan changes on every merge while the harness does not. Recommendation: split the decisions
    (and covers) into a small checked-in file and let the full plan join the model as an ignored artefact.
    With "keep": say so with this number so the question stops reopening.
38. ~~**Fruit of §13, no decision needed** — F42 dropped decisions named (F32, carried twice), F43 the uninstall's
    reporting moves from `cli.py` into `apply`, F44 README quick start and the doctor count, F46 one
    troubleshooting row for `kept, yours` on an older harness, F47 two tests for the untested removal branches
    and the real coverage number (97 %).~~ Built 2026-09-19 as M3j's second slice, with F52, F53 and F55 (§13.1);
    no ADR — behaviour, no decision.

39. **Does M3k move ahead of M3h and the announcement?** The first question a reader asks both Sherpa and
    metaharness is "does it work with my runtime?" (§9.1); today the host list says two. M3k is thin by
    ADR-0050 (`agents-md` already produces what those hosts read), M3h needs a real Hermes launch on the corpus.
    Recommendation: M2c → M3k → M3h, and the announcement after M3k, so the README names six hosts on the day
    it is shown around. Against: ADR-0050 placed M3k after M3h, and Hermes is the runtime with the outcome hook
    already designed (ADR-0023). The order changes nothing in the code of either.

40. **Sherpa's root block pushes a full root `AGENTS.md` over the runtime's ceiling (§14 F68).** The 16-module corpus repository's root file is 32 KB before sherpa; the index block (top 20 units by rank plus the pointer) adds ~1.5 KB and Hermes truncates at 32 KiB — the tail, sherpa's block, is what gets cut. Options: (a) when the file plus the block would cross the ceiling, render the block as its two pointer lines only (`<home>/docs/modules/`, the checker) and say so in the dry run; (b) leave it to C7's line. Recommendation: (a) — sherpa never makes a file the runtime cannot read whole; the index is discovery, the nested files carry the facts. With (b) the team learns it from a truncated prompt.

Decided (2026-09-18): a nested `AGENTS.md` at a unit's own path covers the owner-doc entry by path → ADR-0049.

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

### 9.1 Addendum — metaharness (2026-09-19)

Found the same day the M3j slice landed: [metaharness](https://github.com/ruvnet/metaharness) (ruvnet, MIT,
v0.1 beta, ~660 stars, Rust kernel as WASM plus Node). Same headline — a harness generated from a repository —
different product: it scaffolds a **new** branded npm package (own `npx` CLI, MCP server with default-deny,
signed release manifests, SBOM, memory, model routing) from a static read of manifests and lockfiles; the
recommendation of agents and skills is not explained, there is no git history, no reasoned no, no in-place
write into an existing repository, no adopt, no outcome channel, and its "drift" is drift from its own template,
not from the code. Ten hosts are listed as adapters of the generated package. Plus a browser studio, self-
evolution ("Darwin"), a cost leaderboard — breadth in v0.1.

What it changes for Sherpa: nothing in the thesis (§9: the layer underneath the runtimes, evidence and
discipline), two things in the plan. **Breadth of hosts is now a milestone (M3k, ADR-0050)** instead of a
reaction to the corpus — the first question a reader asks both projects is "does it work with my runtime?",
and "Claude Code plus every `AGENTS.md` reader" is true but invisible in a host list of two. **The README
names the difference in one sentence and names the neighbour under `## Related`** — the differentiator is the
evidence and the no, both of which metaharness cannot show, so it has to be the first thing a reader sees.
Distribution remains the real gap: metaharness has an `npx` one-liner, a web studio and an author with reach;
Sherpa has 0 stars and a private wheel. That is a launch question (ADR-0010's public release), not a code one.

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
| F18 | **A preview failed on configuration: with `.agents/` and `.claude/` both present and nothing decided, `apply --dry-run`, `adopt --dry-run` and `status` stopped with "set `[apply] home`" before listing a file.** | `cli._resolve_layout` raised for every `ask=False` call; first run on a large repository with a hand-written `.agents/` and a cloned `.claude/`: one line of output. | Built: a preview assumes `.agents` (the same default an interactive Enter takes) and prints the assumption after the `targets:` line; `--yes` and a terminal-less write still refuse; no flag — a layout stays a decision (ADR-0036, amends 0015 for read-only runs). |
| F19 | **A `.claude/` that is a repository of its own (a harness kept in a separate clone, `.claude/.git`) received 141 files without a word — tracked by the clone or by nobody, never by the repository `apply` ran in.** | Same run; `_resolve_layout` never looked for `.git` under the home or `.claude/`. | Built: one note per directory (`note: .claude/ is a repository of its own (.claude/.git) — files written there are not tracked by this repository.`) in the dry run, the write and `adopt`; a note, not a refusal (ADR-0037). |
| F20 | **A production install validated nothing: `jsonschema` is a dev extra, `validate()` a no-op without it. `decision: rejcet` passed `plan_from_dict`, `selected()` read it as not rejected and rendered the refused agent; `schema_version: 999` and `kind: wizard` passed too.** | `yamlio.validate`, `state.validate`, `model.validate`: `except ImportError: return`. Reproduced with `sys.modules['jsonschema'] = None`. | Built: `sherpa/schema.py`, a stdlib interpreter for the keyword subset the schemas use, on every reader; `jsonschema` stays the dev reference and `tests/test_schema.py` runs one matrix through both (ADR-0042, amends 0005). |
| F21 | **Non-ASCII paths lost their churn.** `git log --name-only` C-quotes `über.py` as `"\303\274ber.py"` without `-z`; `ls-tree -z` does not; `collect()` dropped the quoted name. Hotspots, authors and module churn wrong for every repository with such a path. | `t0_git.log_since`: no `-z`; reproduced with `normal.py → 1, über.py → 0`. A newline path would also have shifted every `cat-file --batch` answer after it. | Built: `-z` in `log`, NUL parsing; newline paths get no LOC instead of being sent (ADR-0038). Test with umlaut, CJK, tab and newline. |
| F22 | **Coupling counter and printed denominator did not match.** `share = shared / measured commits`, the row said `6 of 15 commits, 50 %` with `commits_90d` — 6/15 is 40 %. | `t1_modules.compute_coupling` vs `render.coupling_row`. | Built: `Coupling.of` in the model (schema v5), row `6 of 12 measured commits, 50 %` (ADR-0039); `status`/`apply` name `sherpa plan` for an older model. |
| F23 | **Outcome labels held false successes and wrong revisions.** `cat pytest.ini` matched `TEST_RE` → `tests_run=1`, exit 0 → `success`; `harness_rev` read at Stop, so an `apply` inside the execution rebooked the label. | `sherpa-outcome.py` `TEST_RE` (substring), `stop()`; reproduced. | Built: `is_test_run` — runner as command word per shell segment, wrappers and paths stripped; `harness_rev` at start, `harness_rev_at_stop` when it moved; 30-case classifier matrix in the tests (ADR-0040). M5 leaves records with `harness_rev_at_stop` out. |

### 10.3 Innovation candidates confirmed

1. **Change coupling as a harness fact** — quotable now that the catch-all is out (F3); the next proof is a
   golden on a fixture with a root bucket showing the partner row without it.
2. **One outcome table across two runtimes per `harness_rev`** (M3h + ADR-0028): nobody measures whether the
   same harness helps Claude Code and Hermes users differently; the hook already accepts both payload shapes.
3. **Stale-plan awareness with zero churn** (F1 + F7): `plan: stale` next to `drift: none` is Terraform's
   "no changes" for documentation, one level up.

## 11. Retro after M3f (2026-09-17) — Sherpa as a harness manager, before M3h

Method: `architect-review` with the focus "Sherpa is a harness manager and generator" (§7 method): the suite and
`ruff`, the four corpus repositories through `scan`, `plan`, `apply --dry-run`, `status`, `check` and
`doctor --offline`, and three lifecycle experiments on the five-module fixture that no earlier retro had run —
an entry rejected **after** it was applied, a unit removed from the trunk, and two branches that both ran
`apply` and were merged. Claude Code's sub-agent and hook documentation read for the premises of the `claude`
adapter. Ten findings; all accepted into the plan by Andrei, decisions as Q26 to Q29.

### 11.1 Gaps

| # | Finding | Evidence | Consequence |
|---|---|---|---|
| F24 ✅ | **No removal path.** After `plan --reject agent:pay` on an applied harness, `apply --dry-run` prints `nothing to do.`; `.claude/agents/pay.md` stays and Claude Code keeps dispatching it. After `git rm -r svc/core` on the trunk, `.agents/docs/modules/core.md` stays. `status` shows `? … in the state, no longer in the plan` and names no way out. | `apply/__init__.py` `write()`: `files = dict(previous.files)` — a record never leaves; `status.py` `ORPHAN`; `adopt` reports the orphan as `sherpa's, unchanged`. Measured on the fixture. | The team's decision has no effect on the harness; orphans accumulate and every runtime loads them. Terraform plans `- destroy` for what it owns. → Q26, an ADR amending 0016 (and 0013 for blocks). |
| F25 ✅ | **Orphans poison the rebuild.** After a state loss (here a merge conflict in `state.json`), `adopt` adopted `.agents/docs/modules/suite.md` and `.claude/agents/pay.md` as "yours" and wrote `covered:` on entries that carry `decision: reject` — rejected *and* covered on the same entry; the runtime still loads the rejected agent. | `adopt` output `a .claude/agents/pay.md → agent pay (name matches)`; the plan with `decision: reject` and `covered:` on `test-infra suite` and `agent pay`. ADR-0022 recognises older stamps, not renderings of entries no longer selected. | A rebuilt state silently turns sherpa's own stale output into a hand-written harness that overrides the team's no. Fix: `adopt` renders **every** plan entry, selected or not, and recognises its own rendering of a deselected entry as `sherpa's, no longer in the plan` — an orphan record, never a cover; `mark_covered` skips entries with a decision; F24's removal is the way out. Extends ADR-0022's pattern list. |
| F26 | **`harness_rev` moves with the Sherpa version, not with what an agent reads.** | `state.py` `harness_rev()` hashes `sherpa {version}`; measured on one state: `0.7.4 → 79814b3256ea`, `0.7.5 → 1bd8ead4acf8`; 14 of 18 recorded files are agent-visible. | Every `self-update` + `apply` starts a new revision; ADR-0028's 30-label threshold restarts although nothing an agent reads changed — M5 would compare tool versions. Terraform keeps `terraform_version` apart from resource identity. → Q27. |
| F27 | **The outcome hook is shell-form `sh -c`; Claude Code runs shell-form hooks through PowerShell on Windows without Git Bash.** | `render.py` `HOOK_COMMAND`; Claude Code hooks documentation: "`sh -c` on macOS and Linux, Git Bash on Windows, or PowerShell when Git Bash isn't installed"; the exec form (`command` + `args`) runs "with no shell involved". No test renders the command string — the script is tested on Windows CI, the wiring is not. | The mandatory minimum (ADR-0008) fails with a non-blocking notice on four events per turn; labels stay empty, the user sees noise. → Q28. |
| F28 | **The agent's `knowledge:` manifest never reaches the agent.** Claude Code: "the body becomes the system prompt"; the front matter is configuration, `knowledge` is not a field, and the field that does preload — `skills:` — is unused. | `render.py` `agent()`; the sub-agents documentation's field table. C3 checks the manifest, the runtime ignores it; only the body's `Read first:` line acts. | The manifest is a checker convention presented as a runtime mechanism. Fix: keep `knowledge:` as the neutral manifest (C3) and let the `claude` adapter also emit `skills: [regenerate-…]` from the same list — adapter only, the core stays neutral (ADR-0015). |
| F29 | **Skeleton owner docs are the harness's own dormant docs, and nothing measures them.** Every owner doc is seeded with four empty sections; on the 122-module corpus repository that is 77 skeletons in 231 files. §1 names dormant docs as the measured weakness of grown harnesses. | `render.py` owner-doc seed; golden `active-owner-doc-pay.md`; corpus plan: 77 owner docs. | The team cannot see which docs were filled since `apply`. Fix (Backstage scorecards / Soundcheck): one `status` line `N of M owner docs are still skeletons (no text outside the facts block)` — the non-block text equals the seed's; `status --json` carries the list. |
| F30 | **Two branches that both run `apply` conflict in `state.json` on every merge** (`applied_at`, `harness_rev`), while `harness-plan.yaml` merged cleanly. The way out (`sherpa adopt` rebuilds; `load` names it) is documented nowhere. | Measured: `CONFLICT (content): .sherpa/state.json`; no troubleshooting row mentions a conflict. | A team hits this in week one; with F25 the fix (`adopt`) currently makes it worse. Fix: one troubleshooting row in `docs/commands/adopt.md` and `docs/reference/files-and-exit-codes.md` — take either side, run `sherpa adopt`; safe once F25 is built. |
| F31 | **`status` gives CI no drift signal.** Exit 1 only on a checker FAIL; drift and a stale plan exit 0. | `status.py` docstring; `cli.py` exit codes. | A "harness current?" gate needs `--json` plus a JSON tool. → Q29. |
| F32 | **Decisions vanish silently when their entry does.** `merge_decisions` counts kept decisions; a reject on a renamed or removed unit is dropped without a line. | `plan/yamlio.py` `merge_decisions`; measured: `1 decisions kept` after the second decision's unit was removed. | A rename (`svc/core → svc/kernel`) reactivates a rejected agent on the next `apply`. Renovate prints every migrated or dropped config key. Fix: `1 decision no longer matches an entry: agent:core (dropped)` on the plan's last line. |
| F33 | **README and §5 said 326 tests; the suite has 400.** | `pytest -q`: `400 passed`. | Invariant 8 (README is truth). Fixed in this revision. |

### 11.2 What holds

- Gate: 400 tests, 98 % coverage, `ruff check` and `format --check` clean, 20 s on Linux.
- Corpus (54 → 20.6k files, 1 → 122 modules): scan 0.58 / 1.15 / 3.49 / 5.25 s, plan ≤ 0.16 s, `check` 0 FAIL
  and `doctor --offline` ready on all four; the notes of ADR-0036/0037 fired nowhere falsely.
- Bloat control: 3 / 6 / 7 / 0 agents on 79 / 122 / 16 / 1 modules — the floors (ADR-0006) hold where the
  quartile alone would propose 31.
- Idempotence after a decision: `plan --reject` then `apply --dry-run` → `0 to change`.
- A torn or conflicted state: `status` and `adopt` name the way out at runtime (ADR-0034) and the rebuild
  itself runs — only its result is wrong (F25).
- Hand edits survive every path measured (`test_adopt_keeps_hand_edits_in_blocks_and_in_base_files`).

### 11.3 Innovation candidates

1. **Deselect = destroy of sherpa's own bytes only, with the decision kept** (F24/F25): no AGENTS.md generator has
   plan/apply/*remove* for documentation; Terraform has it for infrastructure. Smallest proof: reject an applied
   agent → `- removed` in the preview, the hand-edited variant → `yours now`; one test each.
2. **A harness revision that survives tool upgrades** (F26): outcome samples comparable across Sherpa versions —
   the precondition for M5's claim "revision X helps more than Y".
3. **Skeleton ratio as the harness's health metric** (F29): the first number that says whether a team fills what
   Sherpa scaffolds — Backstage scorecards for AI harnesses.

### 11.4 Proposed next step

One slice **M3i — the manager's delete**: F25 (adopt recognises deselected renderings), F24 (removal of own
unchanged bytes), F26 (content-only `harness_rev`), F32 (dropped decisions named); F27, F28, F29, F30, F31 as
fruit in the same PR. It displaces M3h by one slice because every new target multiplies the files that can
orphan, and M5 builds on `harness_rev` — fixing its identity after M5 would invalidate the first samples. The
milestone table and the status line change once Q26 to Q29 are decided.

## 12. Field test on a grown harness (2026-09-17) — Sherpa meets a hand-built `.claude/`

Method: `doctor`, `scan`, `plan`, `apply --dry-run`, `apply --yes`, `status`, `check` and `adopt --dry-run` on a
15k-file .NET monorepo (48 modules, 1016 commits/90d) whose harness had grown by hand for months: 17 agents, 30
owner docs and 12 skills under a `.claude/` that is a repository of its own (`.claude/.git`, excluded in the
outer repository's `.git/info/exclude`), plus `.agents/` with skills and an `AGENTS.md` at the root. The first
real target for the manager role §11 describes; every artefact removed afterwards, the repository byte-identical
to before. Five findings, none of them in §10 or §11.

### 12.1 Gaps

| # | Finding | Evidence | Consequence |
|---|---|---|---|
| F34 | **A nested harness repository is invisible to `adopt`.** `inventory` asks the outer repository which files are ignored and drops them as personal; a `.claude/` clone excluded there is dropped whole. `adopt --dry-run` listed 34 harness files — all under `.agents/` — and 0 of the 51 agents and owner docs under `.claude/`; its gap line said `39 proposed owner docs without an existing doc`. `apply` then wrote 39 owner docs and 11 agents next to the existing ones; only one collided by name (the agent whose file name equalled the module slug, skipped with the `adopt` hint). | `apply/adopt.py` `inventory`: `paths -= gitinfo.ignored(repo, …)`; `cli.py` `_nested_repositories` notes the nested repository but `inventory` does not use it. Measured: `git check-ignore -v .claude/agents/x.md` → `.git/info/exclude:7:.claude/*`. | The owner principle breaks on the first repository that already has an owner doc per module — the case Sherpa was built for. ADR-0037 sees the nested repository and says "not tracked by this repository"; the same knowledge must reach `adopt`. → Q30. |
| F35 | **Hand-named owner docs stay unlinked, or link to the wrong file.** With the ignore filter lifted, `adopt.link` mapped 22 of the 51 files: by slug only where the file name equals the module id; by mentions it put four files on one unit (two `discover-*.md` notes, a dated analysis and the owner doc) and four on another (three notes and the owner doc), and left every abbreviated name (`kes.md`, `wsh.md`, `fev.md`, `pabi.md`) at `no unit matches`; two were `ambiguous`. | `adopt.link`: slug, front-matter name, then `≥ 2` unambiguous path mentions. Measured with `link()` over the 51 files against the model's units. | Even a visible harness gets a second owner doc for a third of its units, and `covered:` would land on an analysis note rather than the owner doc. The link is a decision the team makes once; Sherpa should record and check it, not guess it (Backstage: `catalog-info.yaml` names the owner). → Q31. |
| F36 | **The checker fails on files sherpa never wrote.** C4 walks every `.md` under both homes; a refinement note and a vendored skill with dead relative links produced 42 FAIL — `apply --yes` printed them all, `status` said `check: 42 FAIL, 9 WARN`, `check` exits 1. None of the 42 is in a managed or adopted file. | `check.py` docstring C4: "relative file links in `.claude/**`, `.agents/**`, CLAUDE.md and AGENTS.md"; `run()` collects `d.rglob("*.md")`. `apply` rolls back only on **new** FAILs (ADR-0032), so it wrote. | On a grown harness `sherpa check` is red before Sherpa's first file exists, and stays red; the exit code stops meaning "Sherpa's harness is consistent". → Q32. |
| F37 | **A first `apply` adds 133 files; every module gets three.** 39 owner docs pass the floor (ADR-0014: ≥ 1 commit or dependent, ≥ 5 files), and under `claude` + `agents-md` each is `.claude/docs/modules/x.md` + `x/AGENTS.md` + `x/CLAUDE.md` (one line, `@AGENTS.md`); plus 11 agents, 2 librarians, 2 skills, hook, checker, ignore file, 3 blocks. | Dry run: `133 to add, 3 to change, 0 unchanged, 1 skipped.` The last line counts files, not kinds. | A reviewer sees a 133-file pull request, most of it skeletons (F29), and declines. The count per kind belongs in the dry run's last line; the proximity `CLAUDE.md` doubles the file count for one import line. → Q33. |
| F38 | **Small things seen on the same run.** (a) A top-level `yml/` holding Azure Pipelines templates (`_deploy.yml`, `_build_test_binaries.yml`) is a unit of its own and got an owner doc; its files are not CI definitions under ADR-0044 either — a second real convention next to `pipelines/`. (b) `.claude/settings.json` was tracked by the outer repository although `.claude/.git` exists; the ADR-0037 note "files written there are not tracked by this repository" is then half true — `git ls-files` of the outer repository, not the presence of `.git`, decides per file. (c) `apply --dry-run` refused because `.agents/` and `.claude/` both exist and asked for `[apply] home` — right (ADR-0036), and the run needed a `sherpa.toml` in the repository for it. (d) The outcome hook ran on a `Stop` event with a missing transcript and exited 0. | Plan output: `+ owner-doc yml … 14 files ✓`; `git status`: `M .claude/settings.json`; `git -C .claude ls-files` lists it too. | (a) a `yml/` directory is too generic for a path rule; content detection (top-level `steps:`/`parameters:` in a template) is the next step if it recurs. (b) settled by ADR-0045 — the note became a refusal, tracking inside the clone is no longer Sherpa's question. (c) documented; the dry run could accept `--home` so a look needs no file in the repository. (d) nothing to do. |

### 12.2 What holds

- `doctor` on the repository: 9 ✓, `ready`; `scan` 3.6 s for 15 205 files (4.9 MB model), byte-identical on
  the second run; `plan` 6.3 s, 71 entries, 17 reasoned no's with their floors named; `apply --yes` 1.1 s.
- No overwrite anywhere: the three existing files (`AGENTS.md`, `CLAUDE.md`, `settings.json`) got a block or
  hooks appended, the one name collision was skipped and named, the nested repository was noticed (ADR-0037).
- The removal was exact: the state's 136 records were enough to take every sherpa file out and restore the
  three appended ones; `git status` of both repositories identical to the snapshot before the run — ADR-0017's
  "state is an index over the files" held in the direction it was not designed for.
- Owner-doc facts were right where checked: dependencies, dependents, `tested by`, coupling with its
  denominator (`76 of 137 measured commits, 55 %`), hotspots.
- ADR-0044 (this revision): CI definitions under `pipelines/`, `.pipelines/`, `.azure-pipelines/`,
  `.azuredevops/` — 15 pipeline files found where `ci: []` stood before.

### 12.3 Proposed next step

F34 and F35 go into **M3i** before F24: a removal path is only safe when `adopt` sees what exists, and a
harness that grew by hand is the first thing a removal touches. F36 and F37 are fruit in the same slice. F38(a)
waits for a second occurrence; F38(b) and (c) are one sentence and one flag.

### 12.4 Measured after the first M3i slice (2026-09-17, v0.7.6)

Same repository, same commands. The `.claude/` there is a clone of its own, so `apply` and `adopt` now stop on
the first line — `.claude/ is a repository of its own (.claude/.git) — sherpa works with one repository: move
the clone out of the tree, or run sherpa in that repository` — and the dry runs go on with the same text as a
note, `status` runs as before; `doctor` shows it before any of them — `✗ repositories … apply and adopt refuse`
plus `! layout both .agents/ and .claude/ exist and nothing decides where the core lives` (ADR-0045). That is the decision taken in Q30: the first cut of this slice asked the nested
repository itself and inventoried 1 111 files (34 before), 581 of them a knowledge vault kept inside the clone
as `? … unknown yours`; whose files, whose ignore rules and whose harness those are is a second repository's
question, and Sherpa models one. What the other two ADRs do was measured on that first cut, with the clone's
files treated as this repository's harness: 51 agents and owner docs entered the link step; the heuristic
linked 5 agents and 3 owner docs alone, 13 `docs/modules/` files tied in four groups (three analysis notes and
the owner doc of one module, and so on) and covered nothing — the gaps named each group with `covered: <path>`
as the way out (ADR-0046); archive notes, sync reports and reference pages no longer linked. Four `covered:`
lines written by hand: `39 proposed owner docs without an existing doc` became 31, the four notes *yours,
another file covers the entry*, the `apply` dry run 133 → 129 files (F37 untouched — Q33 open). `apply --yes`
reported `check: 0 FAIL, 42 WARN`, `sherpa check` exited 0, `--strict` showed the 42 (ADR-0047). The
abbreviated names (`kes.md`, `wsh.md`, `fev.md`) stay the team's line in the plan, by design. For this
repository the way to those numbers is now to keep the harness in the repository itself, or to run Sherpa
inside the clone.

## 13. Review at v0.7.6 (2026-09-18) — the whole product, after M3i

Method: `architect-review` without a focus (§7 method): the suite with coverage and `ruff`; the four corpus
repositories through `doctor --offline`, `scan` (timed), `plan`, `apply --dry-run`, `adopt --dry-run` and
`check`; on the Python repository the full round trip `apply --yes` → `apply --remove --yes` against `git
status --ignored`; the AGENTS.md specification read for the premise of the `agents-md` target. Ten findings,
five of them fruit; the decisions as Q34 to Q38.

### 13.1 Gaps

| # | Finding | Evidence | Consequence |
|---|---|---|---|
| F39 | **A nested `AGENTS.md` at a unit's path is not an owner doc to Sherpa.** On the corpus repository with 12 nested `AGENTS.md` (13.8k files, 16 modules) `adopt --dry-run` lists all twelve as `· nested no sherpa markers — apply appends its block` and then `22 proposed owner docs without an existing doc`; `apply --dry-run`: `38 to add, 10 to change` — a skeleton under `.agents/docs/modules/` and a facts block appended into the team's file, per module. | `adopt.kind_of` → `nested`; `_link_entry` links only agents and docs under `docs/modules/` (ADR-0046 §3). The AGENTS.md specification: "Agents automatically read the nearest file in the directory tree, so the closest one takes precedence" (agents.md). | The owner principle breaks on the convention M3h targets. Cover by path — a file at the unit's own path is stronger evidence than any name or mention → Q34. |
| F40 | **First-apply count at scale: 243 files on the 122-module corpus repository**, 229 of them owner-doc files for 77 owner-doc entries; 93 on the 79-module one. | `apply --dry-run` kinds counted: 229 owner-doc, 6 harness, 6 agent, 2 librarian. | Q33 with the number a maintainer of a 20k-file repository sees in the pull request → Q35. |
| F41 | **`harness_rev` still moves with the Sherpa version** (§11 F26, Q27 open). After `--remove` every repository ends at `c18941ba2b37` for 0.7.6 and at another value for 0.7.7 with byte-identical content. | `state.py` `harness_rev()` hashes `sherpa {version}`. | M5's first samples restart at every release → Q36. |
| F42 | **F32 is still open and was carried twice**: a decision on a renamed or removed unit is dropped without a line; `merge_decisions` counts kept decisions only, while `merge_covers` (ADR-0046) already names a dropped cover. | `plan/yamlio.py`; M3i's row lists F32 as moved. | With ADR-0048 the silent reactivation now also removes the old rendering and writes the new one. Ten lines, the pattern exists next to it. **Closed 2026-09-19:** `merge_decisions` returns the lines, `plan` prints them under the entries and the YAML notes carry them once — `agent:pay:svc/pay [reject] is no longer in the plan — dropped`; fixture `test_merge_decisions_names_a_dropped_decision_once_and_writes_it_to_no_entry`, thesis E07. |
| F43 | **The uninstall's reporting lives in `cli.py`.** `cmd_apply` decides when the index goes and composes `kept, yours` and `uninstalled —`; `apply.write()` knows nothing of `--remove`. | `cli.py` `cmd_apply` after `apply.write`. | A second entry point (M7a's `/sherpa-apply`) would copy the logic. Move into `apply`: `Result.uninstalled`, `Result.yours`, printed by `render_result`. **Closed 2026-09-19:** `write(remove=True)` fills `Result.yours`, `uninstalled`, `stray`, `records_kept` and calls `uninstall_index` itself; `render_result` prints the four lines, `cmd_apply` holds none of the words (asserted by `test_the_uninstall_is_reported_by_apply_not_composed_by_the_cli`). |
| F44 | **README and the M2b row say the doctor has nine checks; it has eleven** (ADR-0045). The README quick start has no `adopt`, `check`, `apply --remove` although all three run. | `plan.md` M2b row; `README.md` quick start block. | Invariant 8. **Closed 2026-09-19:** already true on 0.8.2 — the quick start lists `adopt`, `check` and `apply --remove`, the M2b row says eleven; verified in M3j's second slice, nothing to change. |
| F45 | **Q23 is measurable now**: the busiest corpus repository has 24 215 commits in 90 days (`git rev-list --count --since=90.days`); the checked-in plan changes on every merge. | Q23's own flip criterion. | → Q37. |
| F46 | **Removal on a harness written before 0.7.6 is conservative and says so only in the ADR**: a blocks file without the whole-file hash loses its blocks and stays as `kept, yours`. | ADR-0048 Consequences; measured on a clone of this repository before the upgrade path existed. | One troubleshooting row in `docs/commands/apply.md`: run `apply` once, then `--remove`. **Closed 2026-09-19:** the troubleshooting row in `docs/commands/apply.md` — run `apply` or `adopt` once, then `--remove`. |
| F47 | **Coverage is 97 %, the plan and README say 98 %**; the 89 uncovered lines include `_prune_empty_dirs`'s OSError branch and `uninstall_index`'s `left` branch — a read-only directory, a stray file in `.sherpa/`. | `pytest --cov=sherpa`: `TOTAL 3467 89 97%`. | Two tests and the real number. **Closed 2026-09-19:** README and plan §5 said 97 % since revision 26; both branches are covered on 0.8.2 (`_prune_empty_dirs` stops at a non-empty directory in every removal, `uninstall_index`'s `left` is asserted by the stray-file case of `test_remove_is_the_uninstall_and_leaves_only_what_is_yours`). Real number after the slice: 449 tests, 98 % (`TOTAL 3613 89 98%`, i.e. 97.5). |
| F49 | **`apply` could not write at all on a monorepo with a root-level build file** (first real run by the end-to-end agent tester on the 122-module corpus repository, 2026-09-19): the root module's scope is `""`, `_relpath("", …)` counted the empty string as a segment and rendered `../.agents/docs/modules/<root>.md` into the root `AGENTS.md`, C4 failed, the run rolled back. No fixture had a root-level manifest (ADR-0027's dominant-root tests build the model by hand). | `render.py` `_relpath`; `tests/test_apply.py`. | **Closed 2026-09-19:** `_relpath` drops empty segments; `build_root_repo` fixture (root `pyproject.toml` plus one nested module, session-built like the other two) with an end-to-end apply, check, second run; 426 tests. |
| F50 | **A rolled-back first apply is a dead end**: the rollback removed the files but left the empty `.agents/` and `.claude/` it had created — invisible to git — and the next run asked which home to use, or refused without a terminal, without naming the rollback as the cause. | `apply/__init__.py` `_roll_back`. | **Closed 2026-09-19:** the rollback prunes the directories it emptied, like ADR-0048's removal; ADR-0032 amended. |
| F51 | **A dangling symlink named `AGENTS.md` or `CLAUDE.md` crashed the checker** (e2e run on 0.7.9): `sherpa check` exited 1 with a raw `[Errno 2]`, and inside `apply --yes` the pre-write check did the same — nothing written, but no finding named the file. ADR-0031 covers symlinks on the write side only; ADR-0047 wants a finding, never a traceback. | `check.py` `_md_files`. | **Closed 2026-09-19:** a symlink that points nowhere is `C4 <path>: symlink target <t> does not exist` — FAIL in a generated file (sherpa writes none), WARN `(yours)` with a state, exit 0; a symlink that resolves is read like its target. Fixture `test_a_dangling_symlink_named_like_a_harness_file_is_a_c4_finding`. |
| F52 | **`apply` on the modify path prints a WARN count `sherpa check` does not repeat** (`check: 0 FAIL, 6 WARN` from `apply`, `0 WARN` from `check` right after): C8 inside the post-write check is computed against the state before the new one is written. Cosmetic — the exit code and the rollback decision use FAILs only. | `apply/__init__.py` `write`, `check.py` `_check_drift`. | Open, half a day: pass the new state to the post-write check, or drop C8 from it; fixture: apply, reject one entry, apply again, assert the WARN count equals `check`'s after the run. **Closed 2026-09-19:** the state is written before the post-write check and a rollback restores the previous bytes (`_restore_state`, ADR-0032 kept); fixture `test_apply_warn_count_equals_check_right_after` (red on 0.8.2: `4 WARN` vs `0`), thesis E08. |
| F53 | **`apply --remove` names a file it removes in the next line**: `… harness_rev <rev> → .sherpa/state.json` then `uninstalled — .sherpa/state.json … removed too`. Cosmetic. | `cli.py` `cmd_apply`, `render_result`. | Open, an hour with F43 (the uninstall's reporting belongs in one place). **Closed 2026-09-19:** the summary line ends at the `harness_rev` when the index goes; the `uninstalled —` line names `.sherpa/state.json` once; thesis E09. |
| F54 | **The e2e skill drifted from the product in four places** on its first run: T19 deleted the state on an installed harness (the checker copy decides the home, ADR-0036 §3 — nothing is asked), T04 asked for seconds the summary line did not print, the model probe read `as_of` at the top level (it lives at `git.windows.as_of`), T09 could not provoke a *new* checker FAIL from outside. | `.claude/skills/e2e-test/SKILL.md`. | **Closed 2026-09-19:** T19 is two empty homes on the clean corpus (also the F50 regression), the scan line prints `in N.N s`, the probe reads the right key, T09 names the write-error path as the one reachable from outside and the programmatic fixture for the checker path. Rule added to the skill and to `milestone-step`: every e2e finding names its fixture, the fix lands it; the e2e run is part of every tag release. |
| F55 | **A kept decision does not follow a renamed unit** (the own harness after ADR-0054): the decision key is `kind:target:scope` and the target is the manifest name, so `agent sherpa-harness [reject]` was gone after the manifest said `sherparc` and the agent was proposed again. | `yamlio.py` decision carry-over; fixture: a single-manifest repository whose manifest `name` changes between two plans, the rejection must survive. | Open — a decision should follow a unit whose path stays and whose name changes (match on `kind` + `scope` when the target is gone). **Closed 2026-09-19:** a decision follows when one decided entry of that kind and scope left the plan and one new entry of that kind and scope arrived — said once as `agent:beta: [reject] — followed from agent:alpha: (same path, renamed)`, kept by key from then on; two candidates on either side carry nothing and are named as dropped; fixtures `test_merge_decisions_follows_a_renamed_unit_and_stops_at_an_ambiguity`, `test_cli_plan_keeps_a_rejection_across_a_renamed_manifest`, thesis E06. |
| F56 | **`status` assumed `.agents` on two undecided homes without saying so** (e2e run on 0.8.1): `apply --dry-run` and `adopt --dry-run` print ADR-0036's note, `status` listed 243 files of drift with `notes: []` — `cmd_status` discarded the layout notes. | `cli.py` `cmd_status`; fixture `test_cli_dry_run_assumes_a_home_and_the_write_refuses_without_a_terminal` extended to `status` and `status --json`. | **Closed 2026-09-19:** the note is the first of `status`'s notes, text and JSON. The run's six open items went with it: the rollback line reaches stderr as `sherpa apply: …` (`test_cli_rollback_names_itself_on_stderr_too`), `doctor`'s runtime line ends `→ targets: …` and hints when Claude Code is on the `PATH` but not a target (`config.detect_targets`, one rule for `apply` and `doctor`), exit code 2 in the reference, the e2e skill's T11 grep, the apply header counts `selected(plan)` (the outcome entry included — goldens and README from 5 to 6 selected), and a decision address without a kind names the kinds while the list of a kind is capped at five. |
| F57 | **`apply` without `--yes` died with a traceback on Windows CI** (the first e2e job on `main`, T07): a redirected `NUL` passes `sys.stdin.isatty()` there, so `apply` asked `apply? [y/N]` and `input()` raised `EOFError` — exit 1, a traceback, in every Windows job that forgot `--yes`; the home question of ADR-0036 had the same hole. | `cli.py` `cmd_apply`, `_resolve_layout`. | **Closed 2026-09-19:** one `_ask` for both questions — no terminal or EOF on the question is the same answer: the dry run's closing line and exit 0, the home question refuses with the fix named when both homes exist and takes the default when none does. The second Windows run showed the prompt still on the closing line (`apply? [y/N] dry run only …` — `input()` prints it before it reads): EOF ends the prompt's line first. Fixture `test_cli_apply_treats_eof_on_the_question_as_no_terminal`, reading through a real `input()` at EOF; 443 tests. |
| F48 | **Q28 and Q29 open since §11, unchanged.** With ADR-0047 the FAIL exit finally means something; `status --exit-code` on drift would complete the contract (Terraform `-detailed-exitcode`: 0 / 1 / 2). | `render.py` `HOOK_COMMAND`; `status.py` exit rule. | Each under half a day; listed so they are decided, not carried. |

### 13.2 What holds

- Gate: 411 tests in 23 s, coverage 97 %, `ruff check` and `format --check` clean.
- Determinism: two scans on the 79-module corpus repository → identical `md5sum`.
- Corpus (54 → 20.6k files; 1 / 79 / 16 / 122 modules): `doctor --offline` ready on all four; scan 0.07 / 0.47 /
  4.49 / 2.72 s; plan ≤ 0.14 s; `check` 0 FAIL everywhere; ADR-0045 refused nowhere falsely.
- Idempotence: the second `apply --dry-run` after a write is `nothing to do.`, `status` says `drift: none`.
- The M3i acceptance on a foreign repository: `apply --yes` 93 files → `apply --remove --yes` `1 files written,
  92 removed`, index removed → `git status --ignored` byte-identical to before (0 lines before, 0 after).
- Never overwrite, even where the content is wrong (F39): every existing `AGENTS.md` is appended, none rewritten.
- Upgrade tolerance without a migration mechanism: plan and state schemas at `const: 1`, `decisions_of` and
  `covers_of` read the raw dictionary — a bump costs a re-plan and an `adopt`, never a decision.
- Bloat control: 6 / 6 agents on 79 / 122 modules.

### 13.3 Innovation candidates

1. **Measured facts inside the nearest `AGENTS.md`** (F39 turned around): the specification makes the nearest
   file the one an agent reads; nobody generates measured facts — dependents, coupling with its denominator,
   hotspots — into it. Sherpa already writes the block; it only has to stop writing the skeleton beside it.
   Smallest proof: cover by path on the five-module fixture with a pre-existing `svc/pay/AGENTS.md`, one golden.
2. **The clean round trip as a CI contract**: `sherpa apply --yes && sherpa apply --remove --yes && git diff
   --exit-code` — a property no AGENTS.md generator states, let alone tests; one line in `docs/commands/apply.md`.
3. **Skeleton ratio as the harness health metric** (§11 F29, unbuilt): with F39 fixed it becomes measurable on
   AGENTS.md-native repositories too — the number M5 can correlate with outcomes.

### 13.4 Proposed next step

One slice **M3j — owner docs where the team already writes them**: Q34 (a nested `AGENTS.md` covers by path),
Q35/Q33 (kind counts, proximity `CLAUDE.md` opt-in), F42 (dropped decisions named), Q36/Q27 decided in the same
PR, and the fruit F43, F44, F46, F47. Before M3h, because the `hermes` target is the `agents-md` target plus a
root file — and F39 is the `agents-md` target's behaviour on the repositories Hermes users own; shipping M3h
first would demo the skeleton problem to the audience M3h is for. It displaces M3h by one short slice; M5 stays
after M3h and starts on a stable revision.

## 14. Review at v0.8.2 (2026-09-20) — the whole product, after M3j; first slice M3l

Method: `architect-review` without a focus (§7 method): the suite with coverage and `ruff`; the e2e theses on
the 122-module corpus repository; five corpus repositories through `doctor --offline`, `scan` (timed), `plan`,
`apply --dry-run` and `check`, and on the 16-module repository with hand-written nested `AGENTS.md` the full
round trip `apply --yes → status → apply --dry-run → apply --remove --yes` against `git status --ignored`; a probe
of the write path on three `settings.json` shapes and of the state reader on a foreign record; the trunk's own
history for the plan churn. Ten findings; six built the same day as M3l, three decided with their slices, one
recorded as the corpus rule. Decided with this review: **Sherpa's own harness is no longer a test subject** —
evidence comes from two corpus repositories of record (§5); the outcome table that opened this review is the
last number taken from the own repository.

### 14.1 Gaps

| # | Finding | Evidence | Consequence |
|---|---|---|---|
| F58 | **`harness_rev` moved with the sherpa version, and M5's data did not exist because of it.** | The repository running the hook longest: 178 executions over 22 revisions in three days, `success 68 · failed 0 · unknown 110` (62 %), max n per revision 21 — below ADR-0028's 30; `apply --remove` on two corpus repositories ended at the same rev per version. `state.py` hashed `sherpa {version}`; its docstring claimed the opposite. | Every release restarted the counter. **Built as M3l** → ADR-0056: `harness_rev` over the content records, `tooling` apart; the empty harness is `e3b0c44298fc` for every version. |
| F59 | **C7's 8 KiB budget fired on the runtime's own maintainers.** | The corpus repository that is the Hermes runtime: `check` → 8 WARN C7, the team's nested `AGENTS.md` at 8.4–18.8 KB; 9 after `apply` appended its block. ADR-0029 took "~8k recommended" from a comment; the ceiling is 32 KiB. | The M3h audience sees eight warnings about their own files first. **Built**: the budget for files sherpa seeded, the ceiling for the team's (ADR-0056 §4); 0 WARN there now. |
| F60 | **`apply` died with a traceback on a `settings.json` whose `hooks` was not an object.** | `{"hooks": []}`, `{"hooks": {"Stop": "nope"}}`, `{"hooks": {"Stop": ["str"]}}` → `AttributeError` in `_plan_hooks`; `main` catches `ValueError`/`OSError` only; the removal side already guarded the shapes. | The preview crashed on a template file. **Built**: `! hooks is not an object of event lists — yours (skipped)`, a troubleshooting row. |
| F61 | **T22 was red on `main`.** | README said 449 tests, the collector 451; 31 theses, `tests/e2e` had 35; the commit message of #47 carried the old count. | Invariant 8 broke in the pull request that added the gate for it. **Built**: the counts from the collector, the rule in §5 and in `milestone-step`. |
| F62 | **`check` walked git-ignored trees; `adopt` did the opposite.** | A permanent `WARN C7` on an ignored vault in this repository (`.gitignore:23`); `check.py` used a fixed directory list, `adopt.inventory` drops `gitinfo.ignored(...)`. | Two rules for "what is harness"; a vendored `AGENTS.md` was a finding. **Built**: `git check-ignore` in the checker, the deployed copy included (ADR-0056 §5). |
| F63 | **No machine-readable dry run.** | `status`, `check`, `doctor` have `--json`; `apply --dry-run` is prose (`render_actions`). M7a's `/sherpa-apply` would scrape it. | Decided: `apply --dry-run --json` with `status --exit-code` (Q29) as one "CI contract" ADR — **M3m**, the next slice (Terraform `plan -json`, `-detailed-exitcode`). |
| F64 | **Five §11 findings were carried through four reviews** (Q28, Q29, F28, F29, Q36). | §13 F48 "listed so they are decided, not carried" — carried in revision 36. | Decided 2026-09-20: Q36 built (F58); Q29 → M3m; Q28 with M3h; F29 with M5; F28 struck — no runtime reads `skills:` from a knowledge list, the manifest stays the checker's convention. |
| F65 | **`status` listed every revision ever seen, uncapped, by hex.** | 22 lines on the own repository; the label records carry `ts`, unused. | **Built**: the current revision, the five most recent by first label, `and N older revisions — sherpa status --json lists them all`. |
| F66 | **Plan §5 contradicted ADR-0042 on validation.** | §5: "validated on every read and write"; ADR-0042: `state.load` and `model.load` trust their writers. A record `mode: wizard` loaded; `state.validate` had no production caller. | A hand-merged state (§11 F30) reached `apply`. **Built**: `state.load` validates, unknown top-level keys tolerated; §5 says what holds for the model. |
| F67 | **Q37 has its number from the maintainer's own trunk.** | 25 of 51 trunk commits touch `.sherpa/harness-plan.yaml` and `state.json`, the plan carried +645/−503 lines; `status` says `plan: stale` after every squash merge. | Q23's flip criterion met by the author. Decided: split (Q37), a slice after M3h. |
| F68 | **The root `AGENTS.md` of the 16-module corpus repository ends over the runtime's ceiling after `apply`**: the team's file is 32 KB, sherpa's root block adds ~1.5 KB → 33 690 bytes, and Hermes truncates at 32 KiB. Found by thesis T13 on the second corpus of record, its first run there. | `apply --yes` on that repository; C7 now says `> ceiling 32 KiB (root proximity file, yours — the runtime truncates it there)`. | The team is warned, but sherpa caused it. → Q40: shrink the root block to its pointer line when the file would cross the ceiling? |

Seen on the first e2e run on the second corpus of record (thesis assumptions, fixed in M3l): a first dry run lists `~` next to `+` where the team already has `AGENTS.md` files; the `plan` tail carries the cover count; the unit the hand-edit theses pick must not be covered; `git status --short` is parsed by column, not offset; a thesis that creates `.claude/` on a repository without that target removes it again.

Small things seen, not findings: `cli.py` `_dispatch` carries an `if True:`; `cli.py`'s docstring says exit
codes 0/1 while the reference documents 2 (argparse); a thesis skipped on a corpus shape reads `BLOCKED`.

### 14.2 What holds

- Gate: 451 tests, 98 % (`TOTAL 3613 89`), 28 s; `ruff check` and `format --check` clean.
- E2E on the 122-module corpus repository: 33 pass, 1 skip (E06: no manifest carries the unit's name on a
  Gradle repository — a documented skip), 1 fail (T22, F61 — closed in M3l).
- Corpus, five repositories (54 → 20.6k files; 1 / 79 / 122 / 16 / 48 modules): `doctor --offline` ready on
  all five; scan 0.09 / 0.59 / 2.72 / 6.36 / 0.65 s; plan ≤ 1 s; `check` 0 FAIL everywhere; dry runs 10 / 93 /
  243 / 39 / 105 files; 0 / 3 / 6 / 7 / 5 agents.
- M3j on a real repository: 9 covers by path on the 16-module repository, `apply --yes` 39 files in 0.46 s,
  the second dry run `nothing to do.`, `status` `drift: none`, `apply --remove --yes` → `git status
  --ignored` 0 lines.
- Never overwrite, compare-and-swap, the symlink guard and atomic writes each have their test and their thesis
  (T09, T11, E05); the uninstall reports from one place (F43), `apply`'s WARN count is `check`'s (E08).
- Upgrade tolerance: plan and state schemas at `const: 1`; a torn state names `adopt`; a foreign model rescans.

### 14.3 Innovation candidates

1. **A harness revision that survives tool upgrades** (F58, built): the only generator that can say "the same
   harness bytes, N labelled executions each, across releases" — the proof is the outcome table on a corpus
   repository staying one sample across the next two tags.
2. **Measured facts inside the file the runtime's own team writes** (M3j, measured on the Hermes repository):
   9 of 12 nested `AGENTS.md` carry sherpa's facts block with no skeleton beside them and, after F59, no
   warning either. Smallest public proof: one anonymised golden of such a block in the README.
3. **The clean round trip as a CI contract** (§13.3 #2): proven on a foreign 13.8k-file repository in 0.46 s —
   one line in `docs/commands/apply.md` and a README sentence, then a thesis; nothing in the market states it.

### 14.4 Next steps

M3l built the same day (this revision). Then **M3m — the CI contract**: `status --exit-code` (0 / 1 FAIL /
2 drift or stale) and `apply --dry-run --json` (the `Action` list), one ADR, theses on both. It comes before
M3h because the M7a plugin and every CI gate consume those two outputs and the theses stop scraping prose.
M3h follows with Q28; Q37 after it as a slice of its own.
