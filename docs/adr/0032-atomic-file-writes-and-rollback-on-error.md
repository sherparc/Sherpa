# ADR-0032 — Every harness file is written whole or not at all, and a failed write rolls back

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei · **Amended 2026-09-19:** a rollback takes the directories it created with it (§4 below)

## Context

`write()` put harness files down with `Path.write_text` — truncate, then write — and rolled back only when the
checker found a new FAIL. An `OSError` half-way through (disk full, a read-only mount, a permission) left the
first files written, the failing one truncated, and the state untouched: the next run said `not managed —
sherpa adopt` for the new files and `hand-edited` for the torn one. ADR-0017 makes that state rebuildable, but
the user had to notice first. An external review on v0.7.0 simulated it. The index files already went through
`sherpa.atomic` (temp file, `os.replace`); the harness files did not.

## Decision

1. Harness files are written through `sherpa.atomic.write_text` too: a sibling temp file
   (`.<name>.<pid>.tmp`), fsync, `os.replace`. A file is the old one or the new one, never truncated.
2. An `OSError` during the write phase rolls back every file written so far — the same `_roll_back()` the
   checker path uses — and reports `write failed: <path>: <error> — rolled back, nothing written`, exit 1.
   When the rollback itself fails, the report names the paths left behind and the way out
   (`git checkout -- <path>` or `git clean`, then `sherpa adopt`).

## Reasoning

- Ansible's `copy`/`blockinfile` and Git's `*.lock` + rename do exactly this per file; it costs one rename.
- Best-effort rollback plus atomic single files cover the failure the repository can see; a cross-file
  journal (Terraform's state transaction) would be a second source of truth next to Git for a case Git already
  restores.
- Honesty over silence: a rollback that cannot restore says which files and what to run.

## Consequences

- `atomic.write_text` is the only write path for harness and index files; `Result.error`, `Result.left`.
- Tests: an `OSError` on the second file (first removed again, state unchanged), a failing rollback (paths
  named), the temp-then-replace sequence observed.
- A crash between two `os.replace` calls still leaves a partial harness — the state is not written, the next
  `apply` previews the difference, and `adopt` records it. That is the ADR-0017 contract, unchanged.

## Amendment 2026-09-19 — a rollback leaves no directory behind

The first real run on a monorepo with a root-level build file rolled back (a rendering fault, C4) and left
empty `.agents/` and `.claude/` behind — git does not show them, so nothing looked wrong, and the next `apply`
asked which home to use (ADR-0015 §1: both present → ask, refuse without a terminal). A dead end caused by the
rollback itself, with no line naming the cause. Decision: `_roll_back` prunes, for every file it removed
because the run had created it, the directories left empty up to the repository root — exactly what
ADR-0048's removal does — and never a directory that still holds anything. The rule of this ADR is unchanged
in spirit: "rolled back, nothing written" now includes directories. Test:
`test_rollback_takes_the_directories_it_created_with_it`.
