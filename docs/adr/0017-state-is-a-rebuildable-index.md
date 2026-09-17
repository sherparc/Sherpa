# ADR-0017 — The state is a rebuildable index; the harness files are the source of truth

**Status:** accepted · **Date:** 2026-09-17 · **Decision:** Andrei (after reviewing an agent runtime's session-store recovery design)

## Context
`.sherpa/state.json` records what sherpa owns in a repository and the hash it wrote; `harness-plan.yaml` records
the proposals and the human decisions. Both were written with a plain `write_text`: a crash or a full disk in the
middle leaves a torn file, and every later command failed on it with a JSON error and no way out. A lost state
(deleted, not committed, copied files without it) had the same effect through ADR-0016: every generated file
became "somebody's" and was never refreshed again.

Mature agent runtimes separate their persistent data into two classes — a canonical store that is never written
into when corrupt, and derived indexes that may be dropped and rebuilt from it, with a repair command and a
fallback path so that operation continues meanwhile. The same split exists in Sherpa, it only was not named.

## Decision
1. **The harness files are canonical.** Owner docs, agents, skills, proximity files, hooks — with their block
   markers — are the source of truth. Sherpa never writes into what it cannot read (ADR-0016) and never deletes.
2. **The state is a derived index** over those files: which of them sherpa wrote, which blocks, which hashes,
   where the core lives. It must always be rebuildable from the files plus the plan — and `sherpa adopt` is that
   rebuild: a file that equals its rendering is sherpa's, a block that equals its rendering is sherpa's, base
   files are sherpa's by name, everything else is the user's. The `harness_rev` of a rebuilt state after an
   unchanged `apply` is the one `apply` wrote (tested).
3. **Index writes are atomic**: temp file, fsync, `os.replace` — a crash leaves the old file or the complete new
   one, never a torn one (`sherpa.atomic`). This covers `state.json` and `harness-plan.yaml`.
4. **Every reader names the way out.** A torn or foreign state fails with `… is unreadable (<why>) — sherpa
   adopt rebuilds it from the harness files`; `adopt` itself treats it as absent and says so.
5. **Sherpa's footprint answers the layout question during a rebuild**: with both `.agents/` and `.claude/`
   present and no state, the home is the one holding `scripts/sherpa-check.py`; only without that does the CLI
   ask.
6. **Telemetry stays append-only and tolerant**: `outcomes.ndjson` is canonical (labels cannot be rebuilt), one
   line per record, readers skip unparsable lines; the per-session spool file is the hook's own scratch.

## Reasoning
- A backup strategy for the state would protect a file that carries no information of its own. Rebuilding from
  the source of truth is cheaper, always current and testable.
- `adopt` already had to reconcile foreign files with the plan; the rebuild is the same operation with the
  previous state absent — one code path, one set of rules (`docs/commands/adopt.md`).
- Atomic replace is the standard answer for small index files on every platform sherpa supports; SQLite or a
  journal would be a dependency for a problem that `os.replace` solves.

## Consequences
- `sherpa.atomic.write_text`; `State.load` raises with the hint; `cmd_adopt` rebuilds; a `_resolve_layout`
  footprint rule; tests for torn state, rebuilt `harness_rev`, hand-edited blocks after a rebuild, stale base
  files.
- What adopt cannot know it says: a block that differs from the rendering may be a hand edit or an older
  rendering; it stays unrecorded either way and the console line names it.
- For the agent runtime in §0 of the plan the same split applies to sessions: transcript canonical (append-only,
  spool on corruption), search index derived and rebuildable, one repair command — noted there, not built here.
