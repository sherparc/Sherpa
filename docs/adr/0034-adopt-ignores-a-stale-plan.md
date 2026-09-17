# ADR-0034 — `adopt` ignores a stale plan, and no reader fails on a torn state

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei · **Amends:** ADR-0017 (the state as a
rebuildable index), ADR-0019 (a stale plan is refused by `apply`)

## Context

ADR-0017 makes `.sherpa/state.json` an index over the harness files and names `sherpa adopt` as the one way to
rebuild it. ADR-0019 makes `apply` refuse a plan whose trunk moved, like a saved Terraform plan. `adopt` took
the same guard, and `plan` read the state for its `covered:` marks without a fallback. Together this was a dead
end: with a torn state **and** a moved trunk, `plan` failed on the state ("run `sherpa adopt`") and `adopt`
failed on the plan ("run `sherpa plan`"), both exit 1. A torn state alone already stopped `plan` and `status`,
the two commands that do not write a harness file. An external review on v0.7.1 reproduced it.

## Decision

1. `adopt` does not check whether the plan is stale. It imports what is on disk against the plan it finds, as
   `terraform import` needs the resource, not a fresh plan; `apply` keeps the guard.
2. `plan`, `status` and `adopt` treat a torn or foreign state as empty: the message with the way out goes to
   stderr, the command runs on. `apply` still fails on it — it is the one command that writes harness files
   from the index and must not do so from a guess.

## Reasoning

- A rebuildable index must never block its own rebuild, and must never block the commands that do not depend
  on it for correctness: `plan` uses the state only for `covered:` marks, which `adopt` recomputes anyway;
  `status` is the diagnostic command and has to show the picture precisely when something is broken.
- `adopt` writes only the index and the covered marks (ADR-0007). A stale plan changes the rendering it
  reconciles against, at worst turning a `generated` record into an `adopted` one — the safe direction
  (ADR-0016, ADR-0033); the next `plan` + `adopt` corrects it. Refusing bought nothing and cost the way out.

## Consequences

- `cli._load_state_or_empty` for `plan`, `status`, `adopt`; `_refuse_stale` only in `apply`.
- `test_adopt_and_plan_run_on_a_torn_state_after_the_trunk_moved` walks the former dead end both ways;
  `test_status_names_adopt_on_a_foreign_state_schema` now expects exit 0 with the message on stderr.
- `status` on a torn state carries the cause in the report: `state: unreadable — …` and
  `drift: unknown until the state is rebuilt` (JSON: `"state": {"error": …}`, `"drift": []`); drift against an
  empty index would name every file and be wrong, so it is not computed. The checker and the outcomes still run.
