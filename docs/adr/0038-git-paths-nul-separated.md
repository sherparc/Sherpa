# ADR-0038 — Git output is read NUL-separated everywhere: a path with an umlaut, a tab or a newline keeps its churn

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei · **Amends:** ADR-0003 (T0 measurement)

## Context

`list_files` read `git ls-tree -z` and got `über.py`; `log_since` read `git log --name-only` without `-z` and
got `"\303\274ber.py"` — git C-quotes every path with non-ASCII bytes or control characters unless `-z` (or
`core.quotePath=false`) is set. `collect()` keeps only touched files that exist in the tree, so the quoted name
matched nothing: zero commits for the file, wrong hotspots, wrong authors, wrong module churn, and everything the
plan derives from them. Every repository with an umlaut, CJK or a space-free-but-not-ASCII path was affected.
`cat-file --batch` had the mirror problem: its request is newline-delimited, and a path holding a newline would
split into two requests and shift every answer after it.

## Decision

1. `git log` runs with `-z`; the record parser splits on the record separator, then on NUL, and strips the one
   `\n` git puts between the header and the first path. Nothing is unquoted, because nothing is quoted.
2. `blob_contents` answers a path holding a newline with `None` (no LOC, never a hotspot) without sending it —
   `cat-file --batch -z` needs git ≥ 2.43 and would exclude older hosts for a file name no real project has.
3. The test builds a repository with `über.py`, `日本.py`, `tab\tname.py` and `new\nline.py`, two commits each,
   and asserts the churn per file, the hotspots and that the LOC of the files after the newline path are intact.
   On Windows the two control-character names are left out — NTFS refuses them — so the umlaut and CJK
   paths alone cover the C-quoting there.

## Reasoning

- NUL separation is how git wants to be parsed by programs; `core.quotePath=false` still quotes control
  characters and is a user setting sherpa should not depend on.
- One parser for both listings keeps the invariant that a path seen in `log` is the same string as in `ls-tree`.

## Consequences

- `t0_git.log_since`, `t0_git.blob_contents`; `test_scan_counts_churn_on_non_ascii_tab_and_newline_paths`.
- Models of affected repositories change on the next `plan` (they were wrong); the schema is untouched.
