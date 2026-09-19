---
name: milestone-step
description: "The ritual for every step of work on Sherpa: branch, build with tests, revise the plan against the market, ADR per decision, docs and README in step, goldens on purpose, diff shown before the commit, PR with squash merge. Use at the start and the end of every milestone slice."
---

# Milestone step — from a decision to a merged PR

## Use when

- starting a milestone or a slice of one (`task/<topic>` branch)
- finishing it: docs, plan, ADRs, README, goldens, commit, PR
- reviewing whether a slice is really done (the "done when" list below)

## Procedure

1. **Branch**: `git checkout main && git pull && git checkout -b task/<topic>`. Never commit on `main`
   (`.githooks/pre-push` refuses the push).
2. **Design questions first**: where readings differ materially, ask Andrei with a recommendation
   (AskUserQuestion); state the assumptions you make anyway in the report.
3. **Build with tests**: every new function has tests; fixture repos are built programmatically
   (`tests/conftest.py`); goldens in `tests/goldens/` are refreshed only on purpose
   (`SHERPA_UPDATE_GOLDENS=1`). Gate: `.venv/bin/pytest -q --cov=sherpa` ≥ 90 %, `ruff check` and
   `ruff format --check` clean. A new claim in README, CLAUDE.md or an ADR is a new thesis in `tests/e2e`;
   a command whose output changes changes its thesis in the same pull request (`pytest tests/e2e -q`).
4. **Calibrate locally**: run the commands on the local corpus repositories (never named in the repo), dry run
   only, delete every `.sherpa/` you created there.
5. **Plan revision**: `docs/plan.md` — status line, the section of the slice, the milestone table, open
   questions (decided ones struck through with the date). Compare with the market and say what is smarter.
6. **ADR per decision**: `docs/adr/NNNN-<slug>.md` (context, decision, reasoning, consequences) and the index
   row in `docs/adr/README.md`.
7. **Docs in step**: the concept doc (rules), the command reference (`docs/commands/`), `docs/index.md` links,
   `CLAUDE.md` if a rule changed. English everywhere.
8. **README**: status badge, command list, roadmap, test count, examples only from goldens.
9. **Scrub**: `grep -rniE "referenz|reference repo|<customer names>"` on the diff must be empty; no German in
   anything pushed.
10. **Dogfood**: `sherpa status .` in this repo — drift and checker clean (`sherpa apply .` when the facts moved).
11. **Show the diff** (`git diff --stat` + key points) and ask; commit only after a yes. Message: one to three
    full English sentences, no `Co-Authored-By` trailer.
12. **PR**: `gh pr create` with a title and a body that names the ADRs; squash merge; then `git checkout main
    && git pull && git branch -D task/<topic>`.
13. **Release** when the slice bumped the version (`pyproject.toml` and `src/sherpa/__init__.py` together):
    `git tag v<version> && git push origin v<version>` on the merged `main` — `release.yml` tests, builds the
    wheel and creates the GitHub release (ADR-0018). Then `sherpa self-update --check` from an installed copy,
    and **the e2e run** (`/e2e-test`: `pytest tests/e2e` on the corpus repository, ADR-0055) on the tagged `main` —
    every release is measured on a real repository; a FAIL there opens the next slice with its fixture.

## Done when

Tests and lint green on Linux and Windows CI · plan revised · ADR for every decision · concept doc, command
reference and README updated · goldens intentional · scrub empty · diff approved · PR open.
