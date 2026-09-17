# ADR-0047 — The checker's exit code speaks for sherpa's files: C1–C5 FAIL in generated files, WARN elsewhere

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei · **Amends:** ADR-0032 (the "new FAIL"
rollback compares scoped findings)

## Context

C1 to C5 walked every markdown file under both homes. On a grown harness (plan §12, F36) that produced 42 FAIL
before the first sherpa file existed — a refinement note and a vendored skill with dead relative links — so
`apply --yes` printed them all, `status` said `check: 42 FAIL`, and `sherpa check` exited 1 with nothing about
sherpa's harness in it. A gate that is red on day one and stays red is not a gate; `apply` already rolled back
only on **new** FAILs (ADR-0032) because the same problem was visible on its own path.

## Decision

1. With a state, C1 to C5 are FAIL only in files sherpa generated (`origin: generated` in the state). In any
   other file under the homes — adopted or unrecorded, yours either way (ADR-0007) — the same finding is WARN
   with the suffix `(yours)`. C6 (hook wiring), C7 (budgets) and C8 (drift) are unchanged.
2. `--strict` restores FAIL everywhere; without a state nothing is managed yet and every rule is strict — a
   repository that never ran sherpa gets the checker as it was.
3. `apply` checks before and after the write with the files it writes counted as managed (`managed_too`), so a
   first `apply` on a grown harness is scoped the same way as the tenth, and the rollback still fires only on a
   FAIL the write introduced.
4. `check.py` stays one stdlib file; the deployed copy takes `--strict` too and reads the state it already read
   for C8.

## Consequences

- On the measured repository: `apply --yes` prints `check: 0 FAIL, 42 WARN`, `sherpa check` exits 0,
  `--strict` shows the old 42.
- A dead link sherpa's own rendering would produce still fails and rolls back. An adopted file is yours: after
  `adopt` records the whole clone, the 42 stay hints — the alternative, FAIL in every adopted file, would
  turn `adopt` into the step that makes the gate red.
- `status --exit-code` (Q29) can build on this: a red status now means sherpa's harness is inconsistent.
