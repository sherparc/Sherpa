# ADR-0033 — A base file that differs from sherpa's copy is yours after `adopt`

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei · **Amends:** ADR-0017 §2 ("base files are
sherpa's by name")

## Context

ADR-0017 let `adopt` record the base files sherpa names itself — the checker copy, the outcome hook, the
telemetry ignore file — as `generated` whenever they differed from the current rendering, with the hash of the
bytes on disk. The intent was an older copy refreshing itself after a lost state. The effect on a hand-edited
hook was the opposite of ADR-0016: before `adopt`, `apply` said `! hand-edited (skipped)`; after a state rebuild
it said `~ updated` and overwrote the edit. `adopt` cannot tell the two cases apart — it cannot render older
versions. An external review on v0.7.0 reproduced it.

## Decision

A base file that differs from sherpa's current copy is recorded as `adopted` (yours, `differs from sherpa's
copy — yours`), and `adopt` lists it as a gap with the way to a fresh copy:
`<path>: differs from sherpa <version>'s copy — yours; delete it and run `apply` for the current one`.
A byte-equal copy, or one that differs only by an older stamp format (ADR-0022), stays `generated` as before.

## Reasoning

- Between a stale copy that stands one round longer and a hand edit lost silently, ADR-0016 wins: sherpa never
  overwrites what somebody changed. That is `terraform import` — import, show the diff, the human decides.
- No new flag: deleting the file and running `apply` is the refresh, and the gap line says so.

## Consequences

- `adopt._reconcile` for base files, `_gaps` with the base paths and the version; the test
  `test_adopt_keeps_hand_edits_in_blocks_and_in_base_files` walks the whole loop (adopt → dry run → write →
  delete → adopt → fresh copy).
- After an upgrade with a lost state, `status` shows the stale copy as adopted drift-free; the gap line at
  `adopt` time is the one place that names it. `doctor` may later check the deployed copy's version (M3h).
