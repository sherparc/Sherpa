# ADR-0006 — Plan thresholds are relative (percentile) with an absolute floor

**Status:** accepted · **Date:** 2026-09-16 · **Decision:** Andrei (plan revision 2)

## Context
The first plan used absolute thresholds (`commits_90d ≥ 40` for an agent). Absolute numbers do not scale: a
five-person repo with 200 commits per quarter would never get an agent, a fifty-person repo would get one
everywhere. CodeScene/Tornhill therefore define hotspots as percentiles of the codebase itself.

## Decision
- Every threshold = **rank criterion** (percentile or top N over all non-test units) **and** **floor** (absolute
  minimum). Both must hold.
- Defaults: agent = top quartile by `commits_90d` ∧ `commits_90d ≥ 20` ∧ `files ≥ 30` (∧ `authors_90d ≥ 2`,
  ADR-0012); librarian = top 2 by `commits_30d` ∧ (`commits_30d ≥ 30` ∨ `commits_90d ≥ 80`).
- Configurable in `sherpa.toml [plan]`; every `skip` reason names rank and floor with ✓/✗.

## Reasoning
Rank alone fires in quiet repos (top quartile of five sleeping modules), floor alone does not scale. The
combination yields plausible proposals in small and large repos; the reason makes the flip criterion computable
for the reader.

## Consequences
- `plan` needs the unit ranking per metric; it is also in the plan header (`ranking`) for traceability.
- Tests in M2: fixture with 5 modules ⇒ ≥ 1 agent; fixture with 50 modules ⇒ ≤ 13 agents.
