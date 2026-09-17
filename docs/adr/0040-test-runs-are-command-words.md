# ADR-0040 — The outcome hook recognises a test run as the command word, and stamps the revision the execution started with

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei · **Amends:** ADR-0008 (the outcome minimum),
ADR-0028 (the evaluation's denominator)

## Context

`TEST_RE` matched a runner's name anywhere in a Bash command: `cat pytest.ini`, `pip install pytest`,
`grep jest src/` and `echo jest` counted as a test run, and with exit 0 as a green one — the label became
`success`. That poisons the denominator ADR-0028 builds M5 on: not more `unknown`, but false successes.
Separately, `harness_rev` was read at Stop; when `sherpa apply` ran inside the execution the label was booked
against the new harness although the agent had worked with the old one.

## Decision

1. `is_test_run(command)`: the command is split into shell segments (`;`, `&&`, `||`, `|`, newline); each
   segment loses environment assignments and wrappers (`env`, `sudo`, `time`, `uv run`, `poetry run`, `npx`,
   `pnpm exec`, …) and a path before the binary; it is a test run when the first word is a runner binary
   (`pytest`, `jest`, `rspec`, `tox`, …) or the first words form a runner phrase (`python -m pytest`,
   `dotnet test`, `npm test`, `npm run test*`, `go test`, `cargo test`, `make test`, …). The word elsewhere in
   the line is nothing.
2. `start()` records `harness_rev`; `stop()` stamps that one and adds `harness_rev_at_stop` when it differs.
   M5's evaluation leaves records with `harness_rev_at_stop` out of the per-revision comparison.
3. The classifier has a fixed input matrix in the tests — commands that are runs and commands that only mention
   a runner — and every new runner enters both sides. That is the promptfoo idea (fixed cases, assertions)
   applied to a classifier that has no model in it.

## Reasoning

- A hook that labels a `cat` as a passed test is worse than one that says `unknown`: `unknown` is honest, a
  false `success` is a wrong number in the only outcome table there is.
- The revision at prompt time is the one the agent read its harness under; it is the only defensible
  attribution.

## Consequences

- `sherpa-outcome.py`: `is_test_run`, `_RUNNER_BINARIES`, `_RUNNER_PHRASES`, `harness_rev` in the open
  execution, `harness_rev_at_stop`; the deployed copy in this repository is refreshed by `sherpa apply .`.
- Tests: `test_outcome_hook_recognises_a_test_run_only_as_the_command_word` (30 cases),
  `test_outcome_hook_stamps_the_revision_the_execution_started_with`.
- Existing `outcomes.ndjson` files keep their old labels; nothing rewrites history.
