# ADR-0031 — `apply` never writes through a symlink

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei

## Context

`apply` writes with `Path.write_text`, which follows symlinks, and creates parents with `mkdir`, which follows
directory links. An `AGENTS.md` that is a link to a file outside the repository — or a `.claude/docs` that
points elsewhere — takes sherpa's bytes there; nothing in the preview said so. Inside the repository the
popular `AGENTS.md → CLAUDE.md` link is the other half of the problem: written through, one file carries two
state records with two hashes, and the drift report is wrong from then on. An external review on v0.7.0 found
the first half.

## Decision

A target path with a symlink in any component below the repository root is skipped in the preview with
`symlink in the path — never written through (skipped)`, wherever the link points. The write phase checks
again; a link that appeared after the preview is reported as `changed since the preview` (ADR-0030). Real files
next to a link are unaffected: with `AGENTS.md → CLAUDE.md` sherpa manages `CLAUDE.md` and skips the link.

## Reasoning

- `git apply` refuses any patch whose path crosses a symlink, in or out of the tree — the boundary is "the
  path is a link", not "where does it point", because the second question has no safe answer inside the
  repository either (two records, one file).
- In the preview, not only in the write: the user reads the reason before the `y`.
- A skip, not an error: a linked `AGENTS.md` is a legitimate layout; sherpa adds where it can and says why not.

## Consequences

- `apply.THROUGH_SYMLINK`, `_through_symlink()` in `plan_files` and `_reconcile`; tests for a file link out of
  the repository, a directory link, a link to a sibling, and a link that appeared after the preview (skipped on
  Windows without the symlink privilege).
- `adopt` and the checker read through links as before; only writes stop at them.
