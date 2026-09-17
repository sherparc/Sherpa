# ADR-0019 — The facts stamp carries the window end, not the trunk revision

**Status:** accepted · **Date:** 2026-09-17 · **Decision:** Andrei (§6 Q10) · **Implementation:** M3d

## Context
Every managed block — facts in owner docs, proximity blocks, agent scope, skills — ends with a stamp
`origin/main@<rev>, as of <date>`. The retro after M3c (`docs/plan.md` §7.1 G1) measured the consequence: a
merge that touches no unit still moves the rev, so `apply` rewrites every block and reports `~` for all files of
a 122-module repository. The state already records `plan.rev`; the plan header names it too. The alternative —
keep the rev in the stamp but compare blocks without the stamp line — needs a second notion of "unchanged" in
`apply`, `status` and `adopt` for the same effect.

## Decision
The stamp is `as of <date>` only, where the date is the scan window end. The trunk revision stays in
`.sherpa/state.json` (`plan.rev`) and in the plan header — one owner each. A block changes only when a number in
it changes. The date moves with every scan, which is acceptable: it is the fact "these numbers are from this
day", and a scan on the same day with the same trunk yields byte-identical blocks.

## Reasoning
- The rev in a block never carried information that the state did not: nobody reads a SHA in an owner doc.
- Harness churn after every `apply` is the surest way to make a team stop running it; Terraform's answer to the
  same problem is "no diff when nothing changed", and that is the determinism story this ADR protects.
- Comparing without the stamp would keep the churn in git history (the bytes still change) — only the report
  would be quiet.

## Consequences
- M3d changes the four stamp sites in `apply/render.py`, refreshes the goldens on purpose and adds the test
  "two consecutive revs, no activity → `nothing to do.`".
- Existing harnesses show one last `~` per block on the first `apply` after the change (the stamp shrinks);
  documented in the release notes of that version.
