# ADR-0002 — Separation of generic (template) vs. project-specific (adapter)

**Status:** proposed · **Date:** 2026-09-16

## Context
Sherpa's templates originate from harnesses built in practice. Any single harness is n = 1: one author, one
project, one stack. A template derived from it without separation silently bakes that project's assumptions into
every target repo. Sherpa is a generic product; no customer project is named in Sherpa's docs or code.

## Decision
Before M3 every element of the template harness is assigned to one of three classes:

| Class | Examples | Lands in |
|---|---|---|
| **Generic** | owner principle, DERIVED VIEW, `MOVED:`, structural/owner rules of the checker, hook schema, stop gate, outcome label, plan convention, golden-question format | `sherpa/templates/` |
| **Adapter** | code-anchor rule, test-runner script, module layout `src/<Prefix>.*`, trunk name | `sherpa/adapters/<lang>/` |
| **Project-only** | knowledge-base projections, concrete librarian scopes, IDE references | stays in the project |

## Consequences
- The template checker is not copied but split into a generic core plus adapter rules.
- Whatever fits no class is recorded as a question in `docs/plan.md` §6 — never adopted silently.
