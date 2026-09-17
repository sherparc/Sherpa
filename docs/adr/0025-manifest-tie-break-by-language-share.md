# ADR-0025 — Two manifests in one directory: the kind with more source files wins

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei

## Context

T1 makes one module per manifest and one module per directory. When a directory carries two manifests —
`pyproject.toml` next to `package.json` is the common case: a Python service whose front-end tooling lives in
the same root — the alphabetically first manifest won (plan §6 Q4, "becomes a flip criterion if a corpus repo
needs it"). The corpus delivered the criterion: a repository with 6.5k Python files and 2.3k TypeScript files
was a `node` module because `package.json` sorts before `pyproject.toml`. Everything downstream that reads the
kind was wrong with it — the owner doc's ecosystem line, `sub_dirs.source_files` (counted with the node
extensions: a 4.5k-file directory showed 6 source files), the `tests naming it` row, and the depth rule.

## Decision

Among manifests in the same directory the kind with the most files under that directory carrying one of its
source extensions (`KIND_EXTS`) wins; a tie falls back to the manifest name, so the choice stays deterministic.
The whole tree below the directory counts, not only the files the module will own — the tie-break runs before
ownership is known and the difference cannot flip a real majority.

## Reasoning

- GitHub linguist decides a repository's language by share of bytes per language; sherpa measures the same
  thing in files, from data T0 already has. No new I/O, no manifest content read.
- The alphabet is not a rule a user can predict; the language of the files is.

## Consequences

- `scan.t1_modules.kind_share`, used in `find_modules`; one test with a Python majority, a Node majority and a
  tie. Q4 is closed.
- A repository whose root kind flips with the upgrade gets `~ block facts updated` in its owner doc on the
  next `apply` — the facts changed, so the block changes (ADR-0019 still holds: nothing else moves).
