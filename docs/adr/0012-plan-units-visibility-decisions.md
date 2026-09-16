# ADR-0012 — Plan units, visible no's within reach, decisions survive the re-plan

**Status:** accepted · **Date:** 2026-09-16 · **Decision:** Andrei · **Code:** `src/sherpa/plan/`, `src/sherpa/cli.py`

## Context
The first version of the stage-1 rules (`docs/plan.md` §2.2, revision 2), calibrated on a large monorepo, produced
an owner doc for every module including dormant adapters, a librarian for a dot directory full of release markers
(hundreds of commits, no module), no author floor, and about a hundred no's of which most only said
"1 commit ✗ · 1 author ✗". It was also open how a checked-in plan preserves the human's approval across another
`plan` run.

## Decision
1. **Units** = modules (T1) plus depth-1 directories without a module, without a dot prefix, from
   `dir_min_files` up; a root module covers everything. Directories rank on equal terms with modules (the scanner
   provides `authors_90d` per directory for that).
2. **Dormant units** (0 commits/90d and 0 dependents) get no owner doc — but always a visible no with a flip
   criterion plus a summary in `notes`. The user must know; silent omission is forbidden.
3. **Author floor** for agents: `authors_90d ≥ 2` (configurable). What only one person touches needs no agent.
4. **No's only within reach**: agent/librarian no's are listed when the unit meets the rank criterion or the
   commit floor (there the flip criterion is information); generator-dominated units always. The rest is counted
   in one `notes` line so the balance ("59 proposals, 16 no's, 60 out of reach") stays honest.
5. **`decision` survives the re-plan**: entries carry `decision: null | accept | reject`; `sherpa plan` reads the
   existing plan and carries decisions over per `(kind, target, scope)`; invalid values are an error (exit 1).
6. **`plan` scans by itself** when the model is missing or has another `schema_version`; `--rescan` forces it.
   The plan header carries trunk, rev and `as_of` of the model.
7. **YAML with a fixed field order** (`kind` first, `reason` last, `evidence` on one line) instead of
   `sort_keys` — refines ADR-0005: determinism comes from the fixed order, not from sorting.

## Alternatives
- List all no's (Terraform style): rejected; with 44 units that is ~100 lines of noise. Terraform lists resources,
  each of which is a decision — a module with one commit is not.
- Owner-doc floor by files (e.g. ≥ 5): left open; only `apply` will show whether two-file modules are a nuisance.
- Decisions in a separate file (Renovate style): rejected; a reviewer should see proposal and approval in the same
  diff.

## Consequences
- On a large monorepo the plan shrinks from ~100 no's to ~16, all of them with met and unmet criteria side by
  side; infrastructure and pipeline directories become units, dot directories do not.
- `apply` (M3) reads `decision`; `propose` without a decision is asked interactively (ADR-0008).
- Goldens (`tests/goldens/`) freeze the rules; every intended rule change refreshes them visibly in the diff.
