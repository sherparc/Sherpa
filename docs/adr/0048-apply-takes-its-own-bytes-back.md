# ADR-0048 — `apply` takes its own bytes back: removal of what sherpa wrote and nobody changed, and `--remove` as the uninstall

**Status:** accepted · **Date:** 2026-09-18 · **Deciders:** Andrei · **Amends:** ADR-0016 (never overwrite, only
add — now: and take back only its own), ADR-0013 (blocks: a seeded file remembers that it was sherpa's whole),
ADR-0007/ADR-0022 (`adopt` recognises its own leftovers), ADR-0032 (removed files roll back like written ones)

## Context

Sherpa could create, append and merge, never remove (plan §11, F24/F25): after `plan --reject agent:pay` on an
applied harness, `apply` said `nothing to do.` and Claude Code kept dispatching the agent; a unit deleted from
the trunk left its owner doc; a lost state rebuilt by `adopt` turned sherpa's leftover of the rejected entry into
"yours" and wrote `covered:` on the rejected entry. There was no uninstall: the harness written into a 15k-file
repository (plan §12) had to be taken out with a script over the state's file list. Terraform plans `- destroy`
for what it owns and only that; Sherpa is a manager (§11) and needs the same half.

## Decision

1. **A record the plan no longer renders is taken back when its bytes are still sherpa's.** `plan_files` adds
   one `- removed` action per generated state record whose path no target renders (entry-bound files; base
   files only under `--remove`):
   - a managed file whose hash equals the state is deleted;
   - a blocks file that is still sherpa's *whole* — the seed plus its blocks — is deleted; otherwise only the
     blocks whose hash equals the state are cut out, markers included and the blank line `apply` put before an
     appended block, and the file stays (`- block facts removed`);
   - `settings.json` loses sherpa's hook groups — identified by `sherpa-outcome.py`, not hashed, so a hand
     edit elsewhere in the file keeps sherpa's groups from staying — and goes only when nothing else was in it;
   - a hand-edited file or block stays: `! hand-edited — yours now (kept)`; a file already deleted by hand:
     `- already gone — record dropped`. In every case the record is dropped (`forget`).
2. **"Sherpa's whole" is remembered.** A blocks file seeded by `apply` carries the hash of the whole file in its
   record (`FileRecord.hash`, until now managed and json-hooks only); the hash follows every block update while
   the file still equals the seed plus its blocks and is dropped the moment a hand touches anything outside a
   block. A record older than this ADR gets the hash on the next `apply` when the file equals the rendering
   byte for byte; `adopt` sets it when the file equals its rendering. C8 never reads the hash of a blocks file —
   text outside the blocks is the human's by design.
3. **Removal is a write.** The dry run lists it (`N to remove.`), the question or `--yes` applies it, the compare-
   and-swap of ADR-0030 protects it (a file that changed since the preview is skipped), a removed file is
   restored on a rollback from `old` like a written one (ADR-0032), and the post-write check counts files handed
   back as yours (`yours_now`) so a dead link in a kept file is a hint, not a rollback (ADR-0047). A directory
   left empty by a removal goes with it — git tracks none. `status` says per file what `apply` will do
   (`removes it`, `removes sherpa's blocks from it`, `drops the record, the file is yours`).
4. **`apply --remove` is the uninstall.** Nothing is rendered; every generated record is taken back as in 1,
   base files included (checker copy, hook script, the telemetry ignore file, the appended root blocks, the
   hook groups). When no generated record is left, the index files (`state.json`, `harness-plan.yaml`,
   `codebase-model.json`) and the telemetry (`outcomes.ndjson`) are removed too and `.sherpa/` pruned; anything
   else there is named as not sherpa's. Adopted files are never touched and stay recorded only until the index
   goes (`N adopted files stay yours`).
5. **`adopt` knows its leftovers.** `cmd_adopt` renders every entry as if accepted and uncovered
   (`targets_for(…, everything=True)`); a file that equals such a rendering of an entry the plan does not
   select — byte for byte or up to an older stamp — is recorded as `generated` with the entry (`= sherpa's, no
   longer in the plan — apply removes it`), never adopted as yours and never a cover. `mark_covered` never
   covers an entry that carries a decision.

**Acceptance** (plan §3, M3i): `apply` followed by `apply --remove` on a clean repository leaves `git status
--ignored` exactly as it was — merged JSON keys, appended blocks, the index and the telemetry included.
Measured on a clean clone of Sherpa itself: 10 files written, 10 removed, `git status --ignored` identical.

## Consequences

- The three lifecycle experiments of §11 pass as tests (`tests/test_remove.py`): reject after apply, a unit gone
  from the trunk, the uninstall with and without hand edits; plus the F25 rebuild.
- A harness written by a sherpa before this ADR has no whole-file hash on its blocks files: the first `--remove`
  cuts their blocks and leaves the skeletons as `kept, yours` unless an `apply` or `adopt` in between proved
  them sherpa's. Honest, not silent: what cannot be proven sherpa's is not deleted (ADR-0033).
- `status`'s `?` orphan line now names an action instead of "delete by hand — Sherpa never deletes".
- `harness_rev` moves on a removal like on a write; content-only revisions stay Q27.
