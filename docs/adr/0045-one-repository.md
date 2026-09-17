# ADR-0045 — Sherpa works with one repository: a nested repository anywhere in the tree stops `apply` and `adopt`

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei · **Supersedes:** ADR-0037 (a nested
repository under a target directory was named, never refused)

## Context

A repository can hold other repositories: a harness kept in a clone of its own under `.claude/` (ADR-0037), git
submodules, a vendored clone under `src/`. Each is a second place where files are tracked and ignored, and
Sherpa's model — one trunk, one state, one harness whose files the state indexes (ADR-0017) — has no notion of
it. Measured on a grown harness (plan §12, F34): the outer repository excluded its `.claude/` clone in
`.git/info/exclude`, `adopt` asked the outer repository which files are ignored and dropped the whole clone
(0 of 51 agents and owner docs seen), `apply` wrote 39 owner docs and 11 agents next to the existing ones, and
what it wrote there was tracked by the clone, not by the repository it ran in. Asking the nested repository
instead (the first cut of this slice) made `adopt` see 1 111 files — half of them a knowledge vault kept inside
the clone — and raised the next question: whose ignore rules, whose tracking, whose harness. Every answer is a
second repository's, and Sherpa does not model a second repository yet.

## Decision

1. **One repository.** `gitinfo.nested_repositories(repo)` lists every directory below the root that holds a
   `.git` directory or worktree file — dependency and build directories (`SKIP_DIRS`) are not walked; of the
   dot-directories only `.claude/` and `.agents/` are. A 15k-file tree answers in under 0.1 s.
2. **`apply` and `adopt` refuse** when the list is not empty, with one line that names up to five of them and
   the way out: `.claude/ is a repository of its own (.claude/.git) — sherpa works with one repository: move
   the clone out of the tree, or run sherpa in that repository`. Exit 1, nothing written.
3. **Previews go on.** `apply --dry-run` and `adopt --dry-run` print the same line as a note with the suffix
   `— this preview goes on; apply and adopt refuse.`; `status` runs as before — a read-only command never
   stops (ADR-0034's pattern).
4. **`doctor` says it first.** A check `repositories` — `✗` with the same text and fix — so the refusal is
   never the first time a user hears of it; a check `layout` names the other refusal (`apply --yes` with both
   homes undecided, ADR-0036) the same way.
5. `adopt`'s inventory keeps asking the repository Sherpa runs in which files are ignored (ADR-0007); there is
   no second repository to ask any more.
6. When Sherpa learns multiple repositories (M7, librarians across repos), this ADR is the place to revisit:
   the refusal becomes a model.

## Consequences

- A team with a harness clone under `.claude/` cannot run `apply` or `adopt` until the clone is out of the
  tree or Sherpa runs inside it — the alternative named in plan Q30 and taken: correct and narrow beats
  guessing whose files those are.
- Repositories with submodules refuse too. That is the price of the rule as stated; a submodule-only exception
  (gitlinks in the trunk tree are the outer repository's decision) is the first candidate when it bites.
- ADR-0037's note is gone; its test became the refusal's. The `_nested_repositories` helper in `cli.py` is now
  the single text of the refusal and the note.
