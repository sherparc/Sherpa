# Sherpa

Generic harness generator. CLI `sherpa` (`scan | plan | apply | status`), Python 3.12, stdlib-first.
Plan and architecture: `docs/plan.md`. Scanner: `docs/scan.md`. Planner: `docs/harness-plan.md`. Decisions: `docs/adr/`
(index in `docs/adr/README.md`). Field semantics: `src/sherpa/schemas/`.

## Language
- **English everywhere that gets pushed**: code comments, docstrings, docs, ADRs, README, CLI output, test names,
  goldens, commit messages, PR texts. Sherpa is used by developers who do not read German.

## Rules
- Owner principle: every fact has exactly one place. `docs/plan.md` owns architecture and milestones, ADRs own
  decisions, code owns behaviour. No duplicates in README or comments.
- Scanner and applier stay deterministic (no LLM, no network dependency). LLM only in `plan` (stage 2).
- Every generated file carries the `sherpa:generated` marker; hand-edited files are never overwritten.
- Tests: `.venv/bin/pytest -q` from the repo root; lint `.venv/bin/ruff check . && .venv/bin/ruff format --check .` —
  both must be green before every commit (CI runs Linux and Windows; macOS is commented out in the matrix and is only
  enabled, after asking, for large changes to Git/path/encoding logic). Every new function comes with tests; fixture
  repos are built programmatically (`tests/conftest.py`), never checked in as binaries. Coverage target ≥ 90 %
  (`docs/plan.md` §5). Plan goldens live in `tests/goldens/`; `SHERPA_UPDATE_GOLDENS=1` refreshes them after an
  intended rule change.
- Git measurements always against `origin/<trunk>` via `sherpa.gitinfo.resolve_trunk` (ADR-0003), never against `HEAD`.
- Language-agnostic: T0 (Git) and T1 (manifests) must work without language adapters (`docs/plan.md` §2.1).
- Model access only through `sherpa/llm/` (ADR-0004); no LangChain/LangGraph, no provider code elsewhere.
- Before every commit show the diff (`git diff --stat` + key points) and ask Andrei; commit and push only after his yes.
- Never push to `main` directly: every step is branch `task/<topic>` → PR → squash merge (guard: `.githooks/pre-push`,
  enabled via `git config core.hooksPath .githooks`). Remote is `github.com/sherparc/Sherpa`.
- Namespaces (ADR-0009): product and CLI are `sherpa`, the Python package `sherpa-harness`, the GitHub org `sherparc`.
- Commit messages: one to three full sentences, never a `Co-Authored-By` trailer.
- README is marketing and truth at once: it moves with every step (status, roadmap, numbers) and never claims what
  does not run — examples are real outputs, badges only for things that exist.

## Product, not project
- Sherpa is generic. Docs, code, tests and examples name **no** customer project; examples use neutral names
  (`Shop.Pricing`). Industry methods (Terraform plan/apply, Backstage, CodeScene hotspots, Renovate) are first-class
  sources of patterns, not any single harness.
- **Nothing about customer repos or local calibration runs on them lands in this repo**: no mentions of a
  "reference" or template repo, no module counts, plan results or findings derived from scanning a customer's
  code, no `.sherpa/` artefacts left behind there. Calibration happens locally only (`tests/corpus/` is ignored);
  docs argue with fixtures and neutral benchmark figures ("15k-file monorepo: 2.7 s") that name no source. Before
  every commit, grep the diff for "referenz", "reference repo" and customer names — it must be empty.

## Collaboration
- After every step revise `docs/plan.md` critically: against the best established market solutions (Terraform,
  Backstage, Renovate, CodeScene, promptfoo, …) plus own knowledge — propose inconsistencies, missing building blocks,
  better alternatives with reasoning; Andrei decides what enters the plan.
- After every iteration one ADR per decision taken (`docs/adr/`, keep the index). What has no ADR is not decided.
- Teamwork: when unsure or at design decisions ask Andrei, do not decide silently. Report briefly what was done —
  he must always know what is happening.
