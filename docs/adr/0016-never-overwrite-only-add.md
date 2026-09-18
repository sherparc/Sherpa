# ADR-0016 — In the user's repository Sherpa never overwrites what exists; it only adds

**Status:** accepted · **Amended by:** ADR-0048 (sherpa takes back its own unchanged bytes; the rule stays: never another's) · **Date:** 2026-09-17 · **Decision:** Andrei ("if something exists, Sherpa must never overwrite, only add")

## Context
ADR-0013 defined ownership by managed files and blocks with hashes in the state. Two paths still rewrote content
Sherpa had not written: a file whose markers were present but whose state record was missing was treated as
Sherpa's again, and a block with one of Sherpa's names that had no hash in the record was regenerated. Both are
edge cases — a deleted state file, a hand-written block named `facts` — but the rule has to be absolute for a
tool that writes into other people's repositories.

## Decision
`sherpa apply` in a target repository:

1. **Creates** files that do not exist.
2. **Appends** its block to a root or nested `CLAUDE.md`/`AGENTS.md` that exists without it, and **merges** its
   hook entries into `.claude/settings.json`; nothing that was there moves or disappears.
3. **Rewrites only bytes it wrote itself and that nobody changed since** — a managed file or a block whose
   current hash equals the hash in `.sherpa/state.json`. Everything else is skipped and reported with `!`:
   hand-edited files and blocks, blocks removed by hand, blocks with Sherpa's names that Sherpa never wrote,
   files with markers but no state record, files without a state record.
4. **Deletes nothing** — orphans are listed by `status` until a human removes them; a rollback restores exactly
   the previous bytes.

A recorded, unchanged block is refreshed on every apply — that is the point of managed blocks — and Sherpa's
own scripts (checker copy, hook) are updated with a new version as long as nobody edited them. Taking over
foreign files is `sherpa adopt`'s job, and adopt records them as `origin: adopted` without changing a byte.

## Reasoning
- A harness generator that loses one human sentence loses the team's trust for good; a skipped line with a
  reason costs nothing.
- Add-only is also what makes `apply` safe to run from CI with `--yes`.

## Consequences
- `_plan_blocks`: no state record + markers → `! exists with sherpa markers but no state record — sherpa adopt`;
  a block without a hash in the record → `! block <name> not written by sherpa`.
- The rule is an invariant in `CLAUDE.md` and the architect agent; every new adapter is reviewed against it.
- Sherpa's own repository is not the user's repository: there the harness is dogfooded and refreshed freely.
