# ADR-0028 — Outcome evaluation reports counts, not trends, below a floor of labelled executions

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei

## Context

M5 evaluates the outcome labels the hook collects (ADR-0008): success, failed, unknown per `harness_rev`. The
labels depend on the mix of tasks — a question turn is `unknown` by design, a refactoring session produces
test runs, a documentation session none — not only on the harness. Plan §2.5 already says playbooks need ≥ 30
labelled executions; the M5 acceptance said "first 10 executions … regression between two harness versions
visible". Ten executions of different tasks are noise presented as a number — the opposite of the product's
claim. promptfoo compares the same prompts across versions; sherpa's executions are never the same prompts, so
its floor must be higher, not lower.

## Decision

1. `sherpa status` shows, per `harness_rev`, the count `n` of labelled executions and the share of `unknown`
   next to the label counts.
2. A comparison between two revisions ("trend", "regression") is printed only when both revisions have at
   least `outcome_min_n` labelled executions (default 30); below that the line says how many are missing.
3. The share of `unknown` is reported as its own signal: it says whether the hook's signals (test commands,
   PR creation, corrections) fit the team's way of working, and is the first number to bring down.

## Reasoning

- A number with its denominator is honest; a trend line over ten points of mixed tasks is not.
- The product's central claim is "the harness helps, measured" (plan §9). A measurement that a reviewer can
  dismiss as small-sample noise does not prove it.

## Consequences

- M5's acceptance becomes: first 10 executions on a corpus repository with a label ≠ `unknown`; the comparison
  line appears only from 30 per revision; the `unknown` share is shown from the first label.
- `outcome_min_n` joins `sherpa.toml` when M5 is built; `status --json` carries the counts already.
