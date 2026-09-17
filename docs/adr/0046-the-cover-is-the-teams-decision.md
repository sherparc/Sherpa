# ADR-0046 — Which existing file covers a plan entry is the team's decision; the heuristic proposes, never overrides

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei · **Amends:** ADR-0007 (`covered:` came from
the state only)

## Context

`adopt` links an existing agent or doc to a unit by the file's slug or by the unit path it mentions most (at
least twice, unambiguous), and the plan's `covered:` was recomputed from the state on every `plan` — a
hand-written `covered:` did not survive the next run. On a harness that grew by hand for months (plan §12,
F35) the heuristic linked 22 of 51 files. Owner docs named by abbreviation (`kes.md`, `wsh.md`, `fev.md`,
`pabi.md`) matched nothing; four analysis notes under `docs/modules/` mentioned one module as often as its
owner doc, and `mark_covered` took the first path in sort order — `discover-bewilligungsworkflows.md` would have
covered the Dossiers entry, not `dossiers.md`; with ADR-0045 lifting the ignore filter, archive notes and sync
reports under `docs/archive/` and `docs/sync-reports/` linked to units too. Backstage's answer to the same
question is `catalog-info.yaml`: the team names the owner, the tool checks it.

## Decision

1. **`covered:` is a decision.** Written by hand on an entry (`covered: .claude/docs/modules/kes.md`), it is
   carried across re-plans like `decision:` (`merge_covers`), wins over what the state says (`mark_covered`
   fills only entries without one), and is dropped with a note in the plan's tail when the file no longer
   exists (`owner-doc:kes:src/Kes was covered by …, which no longer exists — dropped`). The state's record is
   the second source, and a record whose file is gone covers nothing.
2. **`adopt` honours it first.** A file the plan names on an entry is recorded with that entry — *covered: set
   in the plan* — before name and mention matching run.
3. **Only the owner-doc location links.** A doc is a candidate only under `<home>/docs/modules/`; reference
   pages, architecture notes, archives and reports mention modules and are never owner docs. Agents keep the
   flat `agents/` directory.
4. **One file per entry.** When several files link to one entry, the plan's word beats a name match (or a file
   at sherpa's own path), a name match beats a mention count; the rest are recorded as yours, their row says
   *matches owner-doc pay (…) — yours, another file covers the entry*. Files that tie cover nothing; the gap
   line names them and the way out: `3 files match owner-doc pay (a, b, c) — none covers it; name the owner
   doc on the entry: covered: <path>`. The *no unit matches* gap carries the same hint.
5. The plan schema's description of `covered` says so; no alias table in `sherpa.toml` — that would be the
   same decision in a worse place.

## Consequences

- On the measured repository: four hand-set covers turn 39 proposed owner docs into 31 on the next `adopt`,
  the four analysis notes are yours, and no entry is covered by an archive. The remaining abbreviations are
  one line each in the plan.
- A cover that was set by hand and later contradicts the state (the file moved to sherpa's path, a rename)
  is still the plan's word — the note on a vanished file is the only automatic change.
- `apply` needs no change: `selected()` and the renderer already read `e.covered`; agents and proximity files
  of a covered unit point at the named file.
