# ADR-0037 — A target directory that is a repository of its own is named in the preview and the write, never refused

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei

## Context

Teams keep their agent harness in a repository of its own and clone it into the product repository as `.claude/`
(or `.agents/`), git-ignored — the harness evolves separately from the code. Sherpa's `claude` target writes
`.claude/agents/*.md`, `.claude/hooks/sherpa-outcome.py` and `.claude/settings.json`; the core writes under the
home. Written into such a clone, those files are tracked by the nested repository or by nobody, never by the
repository `sherpa apply` was run in — `git status` there shows nothing, a `git pull` in the clone can drop or
conflict with them, and the outcome hook lives in a repository the checker copy does not see. Measured on a
repository whose `.claude/` carries a `.git` directory: the dry run listed 141 files without a word about it.

## Decision

1. After resolving the layout, `apply` (dry run and write) and `adopt` look for `.git` — a directory or a
   worktree file — directly under the home and, when the `claude` target is on, under `.claude/`. Each hit prints
   one line after the `targets:` line: *note: .claude/ is a repository of its own (.claude/.git) — files written
   there are not tracked by this repository.*
2. It is a note, not a refusal and not a skip: the user may want exactly that layout. Sherpa never writes into
   or reads the nested repository's `.git`.

## Reasoning

- Sherpa's promise is that the harness files are the source of truth and Git carries them (ADR-0017); a nested
  repository silently breaks that promise for the files inside it. Naming it once is the cheapest fix that keeps
  the user's choice.
- `git` itself refuses to add a nested repository's files (`adding embedded git repository` warning); Sherpa
  says the same thing one step earlier, before the files exist.

## Consequences

- `cli._nested_repositories(repo, home, targets) -> list[str]`, called from `_resolve_layout`.
- Tests: `test_resolve_layout_names_a_target_directory_that_is_a_repository_of_its_own`,
  `test_cli_apply_names_a_nested_repository_in_the_dry_run_and_the_write`.
- Not covered: a nested repository deeper than the target directory (`.claude/skills/x/.git`) — no measured
  case; the adopt inventory would list such files like any other.
