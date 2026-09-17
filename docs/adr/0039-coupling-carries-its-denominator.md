# ADR-0039 — A coupling row prints the denominator it was computed with

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei · **Amends:** ADR-0021 §4 (the row format)

## Context

`compute_coupling` divides the shared commits by this module's *measured* commits — those below the size cap,
the excluded root left out (ADR-0021, ADR-0026). The owner-doc row printed `shared of commits_90d` next to the
percentage: `6 of 15 commits, 50 %`, where 6/15 is 40 %. The number was right, the sentence around it wrong; an
agent reading the row cannot tell which, and the reviewer could not reproduce the percentage from the model.

## Decision

`Coupling` carries `of` — this module's measured commits — in the model (schema v5, `required`), and the row
reads `6 of 12 measured commits, 50 %`. `share` is `shared / of`, rounded to two decimals, as before.

## Reasoning

- The three numbers must be reconcilable from the row alone; code-maat prints `revs` and `shared-revs` next to
  the degree for the same reason.
- Storing the denominator instead of recomputing it in the renderer keeps the model the single owner of the
  measurement (the renderer knows no cap).

## Consequences

- `model.SCHEMA_VERSION = 5`; `plan` rescans an older model; `status` and `apply` now name that way out
  (`model has schema_version 4, expected 5 — run `sherpa plan` (it rescans)`) instead of the bare error.
- `render.coupling_row`, the schema description, the owner-doc row in the fixture tests.
