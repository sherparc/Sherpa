# ADR-0014 — Owner docs need a minimum size; a dependent overrides the floor

**Status:** accepted · **Date:** 2026-09-17 · **Decision:** Andrei (plan revision 4, question 6)

## Context
The owner-doc rule was activity only: one commit in 90 days or one dependent. On a 79-module .NET repository from
the local corpus that produced 51 owner docs, 13 of them for units with fewer than five files — test-project
templates and two-file helpers that live outside a test directory. A doc nobody links to is the first to go
stale, and thirteen stale docs cost more trust than they add knowledge.

## Decision
`owner_doc_min_files = 5` in `sherpa.toml [plan]`: a unit with fewer files **and no dependents** gets no owner
doc. Any dependent overrides the floor — a two-file library three modules depend on keeps its doc. Small units
are listed as reasoned no's (`small unit: 3 files. Flips when: files ≥ 5 or dependents ≥ 1`) and counted in a
note that names the key and the override, so the reader in the terminal knows what was left out and why.

## Reasoning
- Files, not LOC: LOC punishes terse languages and rewards generated verbosity; the file count is what a doc
  would have to describe.
- Dependents override because coupling is the reason a doc exists: whoever depends on the unit needs its facts.
- Visible, never silent — the same principle as dormant units (ADR-0012).

## Consequences
- `PlanConfig.owner_doc_min_files`, a second check on every owner-doc entry, a `small units` note.
- On the five-module fixture the three-file `web` module loses its doc (0 dependents); `core` keeps it (2
  dependents). Goldens and README example updated.
