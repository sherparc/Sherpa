# ADR-0055 — The end-to-end theses are pytest: `tests/e2e`, the `sherpa` command on a corpus, in CI

**Status:** accepted · **Date:** 2026-09-19 · **Decision:** Andrei · **Amends:** ADR-0043 (the CI matrix gains a
job) · **Code:** `tests/e2e/`, `pyproject.toml` `[tool.pytest.ini_options]`, `.github/workflows/ci.yml`,
`.claude/skills/e2e-test/SKILL.md`

## Context
The e2e-tester agent (plan §13, F49 onwards) turns every claim of README, CLAUDE.md and the ADR index into a
thesis with a command and a pass criterion and runs the lifecycle on a corpus repository. The first three runs
found six defects the unit tests could not see — and four drifts of the skill itself (F54): the catalogue lived
as prose with shell snippets, executed by hand, and drifted with every command change; a run took an hour of
attention; and it ran only when someone remembered, never on a pull request. The skill's own rule — every
finding names the fixture that will catch it — had no counterpart for the theses: a thesis that held once was
not guaranteed to hold tomorrow.

## Decision
1. **One test per thesis in `tests/e2e/test_theses.py`**, in lifecycle order; the claim and its source are the
   `thesis` marker, the proving output line is recorded through the `ev` fixture and printed in the theses table
   at the end of the run (id · result · claim · source · evidence) — the report shape of the agent, produced by
   pytest. T01–T22 are the catalogue of the skill; E01–E05 are the follow-ups of the first runs (the deployed
   checker standalone under `python -I -S`, the write boundary of `apply`, the configured home, CRLF kept,
   a dangling symlink as a C4 finding).
2. **The product is measured, not the package**: every thesis runs the `sherpa` console script as a subprocess
   with a CI job's environment (no terminal on stdin, `SHERPA_NO_UPDATE_CHECK`, UTF-8) and asserts on exit
   code, stdout, stderr, the files and `git status --short --ignored --untracked-files=all` — never on an
   internal. Numbers are relative (more than none, the same twice), so one test holds on the built-in monorepo
   and on twenty thousand files alike.
3. **The lifecycle is three session fixtures — `planned`, `installed`, `uninstalled`** — each runs its command
   once and keeps the result. A thesis asks for the phase it needs; when the phase's command failed, the thesis
   is BLOCKED (skipped with the failing line), not red for a reason that is not its own. `-k T11` alone runs the
   phases it needs and nothing else. Theses that start from the clean corpus (a write error, a cover by path,
   two empty homes, the follow-ups) take `clean_slate`, which verifies the corpus clean before and scrubs and
   verifies it after — whatever the thesis did.
4. **Two corpora, one suite.** Without `SHERPA_E2E_REPO` the corpus is built programmatically
   (`tests/e2e/corpus.py`: a root-level manifest, an active unit with two authors and a generated directory,
   dependents, a small unit, a dormant unit, a test module, an umlaut path, a bare `origin`) — that is what CI
   runs, in seconds. With `SHERPA_E2E_REPO` the same theses run on the local corpus repository: verified clean
   including ignored files before the first thesis, fetched once, every `scan` and `plan` with `--no-fetch`, the
   harness taken back and the corpus verified clean after the last; its path reads `<corpus>` in the table and
   never enters a file of this repository (CLAUDE.md § Product, not project).
5. **A job of its own in CI**: `e2e (<os>)` next to `pytest` and `ruff`, one Python (3.12), the matrix of
   ADR-0043 — Linux on every pull request, Linux and Windows on `main`, all three on a manual run, never on
   the weekly schedule. `pytest -q` keeps ignoring `tests/e2e` (`addopts` in pyproject) so the unit run, its
   coverage gate and the README's test count stay what they are; `pytest tests/e2e -q` runs the theses.
6. **The skill becomes the procedure, the code owns the theses.** `e2e-test` runs the suite on the corpus
   repository, reads the table, turns a FAIL into a finding in neutral terms with the fixture that will catch it,
   and the release step of `milestone-step` runs it on the tagged `main`. A new claim in README, CLAUDE.md or an
   ADR is a new test with a `thesis` marker; a thesis that a command change makes wrong is a red job, not a
   stale paragraph.

## Alternatives
- **A stdlib script (`scripts/e2e.py`)**: no dependency on pytest and closer to "the checker is a single file",
  but the run needs what pytest already has — a guaranteed teardown, `-k`, assertion introspection, a report hook
  — and the fixtures of `tests/conftest.py` build the corpus.
- **Clone a public repository in CI**: names a corpus in a tracked file, which CLAUDE.md forbids; a real
  repository is the local run's job, the built-in monorepo carries every shape the findings needed.
- **Fold the theses into `pytest -q`**: subprocess tests would count toward nothing (coverage is measured
  in-process) and the unit run would slow down for every developer; a separate job with its own name says
  what broke.
- **Phase fixtures per thesis (fully independent tests)**: each thesis would re-run scan, plan and apply — a
  lifecycle *is* linear, and a phase that fails should block, not repeat.

## Consequences
- 31 tests in `tests/e2e/`, 22 theses of the skill plus five follow-ups; the README's test count stays the unit
  count and names the e2e suite next to it.
- `SHERPA_E2E_REPO` joins the environment table of `files-and-exit-codes.md` (used by the test suite only).
- Windows runs everything but the symlink and the permission theses (E05, T09 — skipped by platform, shown as
  SKIP in the table); a change to the CRLF or path logic is measured on `main` before it reaches a release.
- A docs-only change does not run CI (ADR-0043), so a README test count that drifts is caught by the next code
  pull request's T22, not by the README's own.
