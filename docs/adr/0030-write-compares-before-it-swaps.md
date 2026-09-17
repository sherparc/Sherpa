# ADR-0030 — `apply` compares each file with the preview's read before it writes

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei

## Context

`sherpa apply` reads every target file once, renders the bytes to write from that read (a managed file whole, a
blocks file by replacing only the marked blocks in the read content), prints the preview, asks `apply? [y/N]`,
and writes. Between the preview and the answer the file can move — an editor's autosave, a second agent, a
teammate's `git pull`. The write then put down bytes computed from the stale read: for a blocks file that
silently dropped prose written outside the markers; a rollback restored the same stale read. The checker sees
structure, not lost content, so nothing reported it. That contradicts ADR-0016 in its own words ("never
overwrite what exists"). An external review on v0.7.0 found and reproduced it.

## Decision

`write()` re-reads each file it is about to write and compares the content with the read the action was planned
from (`Action.old`). A file that differs — or that appeared where the preview saw none — is skipped with
`changed since the preview (skipped)`, keeps its previous state record, and is listed after the checker summary.
Everything else is written as previewed. No lock file.

## Reasoning

- Compare-and-swap is the smallest mechanism that keeps ADR-0016 true across the confirmation pause; it is what
  Ansible's idempotent modules and Git's index (`stat` before write) do. Terraform's state locking answers a
  different problem — two runs of the tool at once — and would be a protocol where a comparison suffices.
- Skip, do not re-plan: the user confirmed the preview, not a new plan. The next `apply` plans against the
  file as it is now and says `hand-edited` or `not written by sherpa` as usual.
- Structural check first, rollback unchanged: a skipped file was never written, so a rollback never touches it.

## Consequences

- `apply.CHANGED_SINCE_PREVIEW`, `_reconcile()`; three tests (managed, blocks and hooks changed after the
  preview; a file that appeared; a rollback next to a skipped file).
- Two `sherpa apply` running at once are still not serialised; the comparison makes the second one skip what
  the first wrote in between. A lock file becomes a question when Sherpa runs as a runtime (plan §0).
