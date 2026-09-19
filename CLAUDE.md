# Sherpa

Generic harness generator. CLI `sherpa` (`scan | plan | apply | adopt | status | check | doctor | self-update`), Python 3.12, stdlib-first.
Plan and architecture: `docs/plan.md`. Documentation: `docs/index.md` (landing), `docs/commands/` (reference per
command), `docs/concepts/` (rules and formats), `docs/reference/` (configuration, files, exit codes). Decisions:
`docs/adr/` (index in `docs/adr/README.md`). Field semantics: `src/sherpa/schemas/`. The repo carries its own
harness: `.claude/agents/architect.md` (overview and reasoning), `.claude/agents/e2e-tester.md` (the product
measured on a corpus repository, skill `e2e-test`, command `/e2e-test`), skills `architect-review`, `milestone-step`
and `sync-kb`, and the files `sherpa apply .` generates (owner doc, hook, checker, the block at the end of this file).

## Language
- **English everywhere that gets pushed**: code comments, docstrings, docs, ADRs, README, CLI output, test names,
  goldens, commit messages, PR texts. Sherpa is used by developers who do not read German.

## Rules
- Owner principle: every fact has exactly one place. `docs/plan.md` owns architecture and milestones, ADRs own
  decisions, code owns behaviour. No duplicates in README or comments.
- Scanner and applier stay deterministic (no LLM, no network dependency). LLM only in `plan` (stage 2).
- **In the user's repository Sherpa never overwrites what exists — it only adds** (ADR-0016): create, append,
  merge; rewrite only its own bytes that nobody changed since (hash in the state). Sherpa owns only what is
  between `sherpa:begin`/`sherpa:end` markers or whole files it deployed (ADR-0013). The core is runtime-neutral (`home`); runtime-specific files
  live in one adapter each in `apply/render.py` (ADR-0015) — a new runtime is a new adapter, never a change to the core. `src/sherpa/check.py` stays a single stdlib-only file — it is
  deployed as a copy into target repos. The harness files are the source of truth and `.sherpa/state.json` a
  rebuildable index over them (ADR-0017): index files are written through `sherpa.atomic`, and `adopt` rebuilds a
  lost state — never add a second way to recover.
- Tests: `.venv/bin/pytest -q` from the repo root; lint `.venv/bin/ruff check . && .venv/bin/ruff format --check .` —
  both must be green before every commit. CI (ADR-0043): Linux on every pull request, Linux + Windows on `main`,
  macOS once a week on `main`; a manual run (`gh workflow run ci.yml --ref <branch>`) covers all three and is the
  way, after asking, to check a large change to Git/path/encoding logic before it merges. Docs-only changes do
  not run CI. Every new function comes with tests; fixture
  repos are built programmatically (`tests/conftest.py`), never checked in as binaries. Coverage target ≥ 90 %
  (`docs/plan.md` §5). Plan goldens live in `tests/goldens/`; `SHERPA_UPDATE_GOLDENS=1` refreshes them after an
  intended rule change.
- Git measurements always against `origin/<trunk>` via `sherpa.gitinfo.resolve_trunk` (ADR-0003), never against `HEAD`.
- Language-agnostic: T0 (Git) and T1 (manifests) must work without language adapters (`docs/plan.md` §2.1).
- Model access only through `sherpa/llm/` (ADR-0004); no LangChain/LangGraph, no provider code elsewhere.
- Before every commit show the diff (`git diff --stat` + key points) and ask Andrei; commit and push only after his yes.
- Documentation moves with every command change: the reference page in `docs/commands/`, the concept doc, the
  index. The pages are written for the web documentation: synopsis, options, inputs and outputs, exit codes, real
  examples (from goldens), troubleshooting.
- Never push to `main` directly: every step is branch `task/<topic>` → PR → squash merge (guard: `.githooks/pre-push`,
  enabled via `git config core.hooksPath .githooks`). Remote is `github.com/sherparc/Sherpa`.
- Namespaces (ADR-0009, ADR-0054): product, CLI and import package are `sherpa`; the PyPI package and the GitHub org are
  `sherparc`.
- Commit messages: one to three full sentences; every commit signed off (DCO, ADR-0052 — `git commit -s`, or once per
  clone `git config core.hooksPath .githooks`, whose `prepare-commit-msg` adds the line), `Signed-off-by` the only
  trailer, never `Co-Authored-By`.
- Releases (ADR-0018): bump `pyproject.toml` and `src/sherpa/__init__.py` together on the branch, merge, then
  `git tag v<version> && git push origin v<version>` — `release.yml` builds the wheel and creates the GitHub
  release; it refuses a tag that does not match both versions. Only `src/sherpa/` ships.
- README is marketing and truth at once: it moves with every step (status, roadmap, numbers) and never claims what
  does not run — examples are real outputs, badges only for things that exist. The README roadmap and plan §3 are
  the same table: same rows, same order; the README says it in one or two sentences, the plan explains and
  carries the acceptance. Whoever touches one touches the other.

## Product, not project
- Sherpa is generic. Docs, code, tests and examples name **no** customer project; examples use neutral names
  (`Shop.Pricing`). Industry methods (Terraform plan/apply, Backstage, CodeScene hotspots, Renovate) are first-class
  sources of patterns, not any single harness.
- **Nothing about customer repos or local calibration runs on them lands in this repo**: no mentions of a
  "reference" or template repo, no module counts, plan results or findings derived from scanning a customer's
  code, no `.sherpa/` artefacts left behind there. Calibration happens locally only (`tests/corpus/` is ignored);
  docs argue with fixtures and neutral benchmark figures ("15k-file monorepo: 2.7 s") that name no source. Before
  every commit, grep the diff for "referenz", "reference repo" and customer names — it must be empty.
- Local test corpus: open-source repositories cloned next to this repo (never named in code, docs, tests or
  commits; the list lives in Andrei's and Claude's memory). Every feature is smoke-tested on all of them — scan,
  plan, apply dry run, check — and the `.sherpa/` artefacts are deleted afterwards.

## Knowledge base
- `kb-sherpa/` is an Obsidian vault: a one-way projection of README, CLAUDE.md, `docs/`, the harness under
  `.claude/` and the schemas, produced by `python3 scripts/sync-kb.py` (skill `sync-kb`, command `/sync-kb`;
  the local Stop hook in `.claude/settings.local.json` runs it after every turn). It is ignored by git together
  with `.claude/memory/` and `.claude/settings.local.json`. Never edit a note there — edit the source and sync.

## Collaboration
- After every step revise `docs/plan.md` critically: against the best established market solutions (Terraform,
  Backstage, Renovate, CodeScene, promptfoo, …) plus own knowledge — propose inconsistencies, missing building blocks,
  better alternatives with reasoning; Andrei decides what enters the plan. The full, read-only form of this is the
  skill `architect-review` (`/architect-review [focus]`): findings with evidence, nothing implemented.
- After every iteration one ADR per decision taken (`docs/adr/`, keep the index). What has no ADR is not decided.
- Teamwork: when unsure or at design decisions ask Andrei, do not decide silently. Report briefly what was done —
  he must always know what is happening.

<!-- sherpa:begin harness -->
## AI harness (managed by sherpa)

Module facts live in `.claude/docs/modules/` — one owner doc per module, the single place
for a fact. Agents in `.claude/agents/` carry a role and a knowledge manifest, never facts;
skills in `.claude/skills/` are procedures. Blocks between `sherpa:begin` and `sherpa:end`
markers are regenerated by `sherpa apply` — write outside them. Integrity: `sherpa status`
or `python3 .claude/scripts/sherpa-check.py`.
<!-- sherpa:end harness -->
