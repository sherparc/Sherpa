# ADR-0007 — Existing harnesses are taken over with `sherpa adopt`, never overwritten

**Status:** accepted · **Date:** 2026-09-16 · **Decision:** Andrei (plan revision 2)

## Context
Target repos often already have a `.claude/` — a mature harness easily holds a dozen agents and several
librarians. An `apply` that only knows "create new" could not run there or would destroy hand-made work.
Terraform solves the same problem with `import`: existing resources enter the state without being changed.

## Decision
A dedicated command `sherpa adopt` (details in `docs/plan.md` §2.6): classifies `.claude/**`, writes every file
as `origin: adopted, hand-edited: true` into the state, links it to modules of the model and reports gaps as plan
entries. `apply` never touches adopted files; `status` treats them like hand-edited ones.

## Reasoning
- Without adopt, Sherpa is only usable for greenfield repos — the minority.
- Adopt turns repos with an existing harness into executable regression cases: the same analysis that is done by
  hand today.
- Separation from `apply` keeps `apply` purely deterministic; `adopt` is read + state write.

## Consequences
- The state schema gets `origin: generated | adopted` and `hand-edited`.
- Classification via path + front matter; unknown files become `kind: unknown` and are named in the report, never
  guessed.
- Part of M3.
