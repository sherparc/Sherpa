# ADR-0008 — `apply` shows the file diff first; the outcome minimum is part of every `apply`

**Status:** accepted · **Date:** 2026-09-16 · **Decision:** Andrei (plan revision 2)

## Context
Approval happens at plan level (YAML, ADR-0005), but the human wants to see *which files* will be created before
anything is written — `terraform plan` shows every resource with +/− before `apply` acts. Second, the outcome
channel was "always first" in the plan but scheduled as milestone M5 after `apply` (M3) — the classic mistake seen
in practice: when the signal is added after the features, executions stay unlabelled and nothing can be measured.

## Decision
1. **Dry run is the default.** `sherpa apply` lists every file as `+ new`, `~ updated`, `= unchanged`,
   `! hand-edited (skipped)` with a hash and then asks. `--yes` skips the question (CI), `--dry-run` stops after
   the list.
2. **The outcome minimum belongs to `apply`** (M3): hook set, label file, `harness_rev` = hash of plan + Sherpa
   version. A harness without a signal is not created. Evaluation (`status`: labels per `harness_rev`, trend)
   follows in M5.

## Reasoning
- The dry run makes the determinism guarantee visible: the same list on a second run = nothing to do.
- `harness_rev` from day 0 allows measuring harness versions against each other later; retrofitting loses the
  mapping.

## Consequences
- `apply` has two phases: `plan_files()` (pure, testable) and `write_files()`; tests check both separately.
- Hook set and label format become a generic part of the templates (ADR-0002).
