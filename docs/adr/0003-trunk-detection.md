# ADR-0003 — Scan always against `origin/<trunk>`, trunk detection in a fixed order

**Status:** accepted · **Date:** 2026-09-16 · **Code:** `src/sherpa/gitinfo.py`, tests `tests/test_gitinfo.py`

## Context
The local `HEAD` is usually on a task branch; measurements against it look plausible and are wrong (trunk
discipline, a lesson from harness analysis practice). Sherpa only gets a path and must find the main branch itself.

## Decision
1. No scan without a remote `origin` (error, no fallback to local branches).
2. `sherpa scan` runs `git fetch origin` (disable with `--no-fetch`), then:
3. Trunk in this order:
   - `trunk` from `sherpa.toml` (override, with or without the `origin/` prefix)
   - `refs/remotes/origin/HEAD` — set by `git clone`; if missing: `git remote set-head origin -a`
   - first existing candidate: `main`, `master`, `dev`, `develop`, `trunk`
4. The model carries `trunk.ref`, `trunk.source`, `trunk.rev`; all churn numbers refer to `trunk.rev`.

## Consequences
- Reproducible: same `trunk.rev` → same model, independent of the checked-out branch
  (`test_scan_ignores_local_branch_and_worktree`).
- A repo with an unusual main branch needs one line of config instead of a heuristic that guesses.
