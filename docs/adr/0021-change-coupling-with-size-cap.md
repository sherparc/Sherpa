# ADR-0021 — Change coupling per module, measured only on commits below a size cap

**Status:** accepted · **Date:** 2026-09-17 · **Decision:** Andrei (architect review before M3d, finding #3)

## Context
The retro after M3c (`docs/plan.md` §7.1 G4) named temporal coupling — "in 15 of 24 commits touching `pay`,
`core` changed too" — as the fact an agent needs first when it lands in a module, and as the first measured
fact the market's AGENTS.md generators do not carry. The scanner already parses `git log --name-only` for churn,
so the commit → modules mapping is free. The review before M3d measured the naive version on Sherpa's own trunk:
14 non-merge commits in 90 days, every one a squash-merged PR touching docs, tests, README and several modules —
coupling of everything with everything at 100 %. Every team using "squash and merge" (GitHub's default option)
has this shape; a `changes together with` row that reads "100 %" everywhere is wrong and would discredit the
row where it is right.

## Decision
1. **Model v4 carries `coupling` per module**: up to three partner modules, each with the number of shared
   commits and the share of this module's measured commits, descending by shared commits, ties by name. Floors:
   ≥ 5 shared commits and ≥ 30 % — below that a partner is not listed.
2. **Commits above a size cap are excluded from coupling only.** Cap = max(5, ⌈modules / 2⌉) modules per commit;
   a commit touching more is a squash merge, a mass rename or a format run — CodeScene excludes large changesets
   for the same reason, code-maat has `--max-changeset-size`. Churn and hotspots still count every commit.
3. **The model says what it skipped**: `coupling.cap`, `skipped_commits`, `measured_commits` and the floors are
   in the model header, so a reader can tell "no coupling" from "no measurable commits".
4. **One row per facts block and proximity block**: `changes together with: core (15 of 24 commits, 62 %)`.
   Sub-units (ADR-0020) carry no coupling row — coupling is measured between modules, where the manifest draws
   the boundary.

## Reasoning
- Tornhill's temporal coupling is the one measured fact about a module that neither static dependencies nor
  file hotspots show; it is cheap, deterministic per rev and answers the agent's first question ("what else do I
  have to touch?").
- A relative cap with a floor keeps small repositories measurable (three modules: a commit touching all three
  is the normal case, not noise) and still cuts the squash-merge shape (122 modules: the cap is 61, a merged PR
  touching 20 modules still counts, a repository-wide rename does not).
- Reporting the skipped count keeps the number honest — the alternative (silently measuring on the remaining
  commits) hides why a coupling is missing.

## Consequences
- `codebase-model` schema 3 → 4 (with `sub_dirs`, ADR-0020, in one bump); `plan` rescans an older model.
- `t1_modules.compute_coupling` is the single implementation; `scan` keeps its stats for the model header.
- Open: coupling between sub-units of a single-manifest repository, once the sub-units have proven themselves.
