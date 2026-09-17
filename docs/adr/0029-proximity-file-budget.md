# ADR-0029 — Proximity files have a size budget: 8 KiB nested, 32 KiB at the root

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei

## Context

The checker's C7 budgets (agent 150 lines, owner doc 600, skill 250) cover the files under the homes, not the
proximity files `CLAUDE.md`/`AGENTS.md` that the runtimes load by themselves. Verified in Hermes Agent's source
on 2026-09-17 (`agent/subdirectory_hints.py`): a nested `AGENTS.md` is injected whole into a tool result on the
first touch of its directory, with a hard ceiling of 32 KiB (head and tail kept, the middle cut) and the
comment "keep area AGENTS.md files well under it (~8k)" — the same comment names Codex's `project_doc_max_bytes`
default as the source of the 32 KiB. The corpus has a hand-written root `AGENTS.md` of 142 KB and a nested one of 9.9 KB.

## Decision

C7 gains two budgets in bytes: a nested `CLAUDE.md`/`AGENTS.md` over 8 KiB and a root one over 32 KiB are
WARNs (`9886 bytes > budget 8 KiB (nested proximity file)`). Sherpa's own nested files stay far below (a facts
block is a few hundred bytes); the rule is for what teams write around the blocks.

## Reasoning

- The number comes from a runtime's measured behaviour, not from taste; the message names the ceiling.
- Bytes, not lines: the runtimes count characters.

## Consequences

- `check.PROXIMITY_BUDGETS`, one test with both budgets at their edge; the deployed checker copy refreshes on
  the next `apply`.
- M3h's acceptance includes the rule firing on a corpus repository with an oversized nested file.
