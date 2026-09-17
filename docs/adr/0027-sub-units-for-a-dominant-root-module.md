# ADR-0027 — The depth rule also runs on a root module that holds most of the repository

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei

## Context

ADR-0020 gives a single-manifest repository sub-units by the depth rule and stops there: as soon as a second
manifest exists, the root module is one unit. The corpus showed the shape this misses — a root package with a
few sub-manifests (`web/`, `tests-js/`, a sidecar): 16 modules, the root module holding 64 % of the files,
`sub_dirs` with 797 entries and depth-1 directories of 4.5k, 1.2k and 788 files — served by one owner doc and
one agent. This is the most common service layout, not an edge case.

## Decision

The depth rule (ADR-0020, unchanged) also runs on a root module that exists next to other modules when it
holds at least `root_share` of all modules' files; `root_share` is a `[plan]` threshold with the default `0.5`,
recorded in the plan header like every other threshold. The console note says why the rule fired:
`N sub-units of <root> (64% of the files, root_share 0.5) by the depth rule (depth 1): …`. `[plan] units`
overrides it as before. Every other rule — floors (ADR-0014), ranks, reasoned no's — applies to the sub-units
unchanged.

## Reasoning

- The trigger is a measurement the model already carries; a share, not a count, so it holds from a 60-file
  service to a 20k-file monorepo (ADR-0006's relative-with-floor idea).
- 0.5 is the point at which "the root module" and "the repository" are the same thing for a reader.

## Consequences

- `plan.rules.units_and_note`, `PlanConfig.root_share`; the poly golden gains one threshold line.
- Corpus check: the 16-module repository gets 9 sub-units at depth 1; the 122-module one (root module 10 %)
  and the 79-module one (no root manifest) are unchanged.
- Open: the owner-doc floor by files for packages with few large files (plan §6 Q15) now matters for more
  repositories.
