# ADR-0022 — `adopt` recognises older stamp formats as sherpa's own rendering

**Status:** accepted · **Date:** 2026-09-17 · **Decision:** Andrei (architect review before M3d, finding #1) ·
**Amended by:** ADR-0049 (older seeds outside the markers are modernised like older stamps)

## Context
`adopt` rebuilds a lost state by comparing every block with its current rendering: equal → sherpa's, recorded
with its hash; different → a hand edit that stays (ADR-0017). ADR-0019 changes the rendering of every block —
the stamp shrinks from `origin/main@<rev>, as of <date>` to `as of <date>`. With a state present that is
harmless: `apply` compares the bytes on disk with the hash in the state, sees "unchanged since I wrote it" and
rewrites the block. Without a state — the case `adopt` exists for — every block written by sherpa ≤ 0.5.0 would
differ from its 0.6.0 rendering, be classified as a hand edit, and never be refreshed again, without a message.
The command whose purpose is recovery would silently freeze the harness.

## Decision
1. **`render.LEGACY_STAMPS`** is a list of older stamp patterns with their rewrite to the current form, newest
   first; `modernize_stamp(text)` applies them. Today it holds one entry: the ≤ 0.5.0 format.
2. **`adopt` compares twice**: bytes equal → sherpa's; otherwise, with the stamp modernised, equal → still
   sherpa's, recorded with the hash of the bytes *on disk* (so the next `apply` sees "unchanged since the state"
   and rewrites it) and reported as `block facts carries an older stamp — apply refreshes it`. Only what differs
   beyond the stamp is a hand edit, and the message now says `(hand edit)` without the hedge.
3. **Every future change to a block's fixed text adds a pattern** to `LEGACY_STAMPS` (or a sibling list for
   non-stamp text) in the same PR, with the test "old bytes → delete state → adopt → apply → `nothing to do.`".
   The list is Sherpa's config migration in the sense of Renovate: old renderings are understood, never
   silently disowned.

## Reasoning
- The rebuild is the recovery path (ADR-0017); a recovery that loses ownership silently is worse than none.
- Recording the on-disk hash keeps one notion of "unchanged" — `apply`'s — instead of teaching `apply` about
  legacy formats too.
- A regex list costs nothing and is testable per entry; a version-aware renderer (render as 0.5.0 would have)
  would drag every old template along forever.

## Consequences
- Test `test_adopt_recognises_an_older_stamp_and_apply_refreshes_it` proves the path end to end.
- `docs/commands/adopt.md` documents the extra row in the reconcile table.
- The pattern list grows with the rendering; a change to the fixed text of a block without a pattern is a
  review finding.
