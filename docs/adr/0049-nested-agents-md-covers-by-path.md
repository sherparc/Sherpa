# ADR-0049 — A nested AGENTS.md at a unit's own path covers its owner-doc entry by path

**Status:** accepted · **Date:** 2026-09-18, revised 2026-09-19 after the review of the first cut · **Deciders:**
Andrei · **Amends:** ADR-0046 (what may cover an owner-doc entry), ADR-0022 (older renderings: seeds, not only
stamps) · **Touches:** ADR-0015 (the `agents-md` target on repositories that already keep nested files),
ADR-0017 (the cover is rebuilt from the files)

## Context

The AGENTS.md convention is proximity loading: "agents automatically read the nearest file in the directory
tree, so the closest one takes precedence" (agents.md). A team that keeps `gateway/AGENTS.md` has its owner doc
there — the strongest evidence there is, an exact match on the unit's `scope`, no heuristic (Backstage: the
`catalog-info.yaml` next to the code is the owner). Sherpa did not see it (plan §13 F39, measured on the
16-module corpus repository with 12 nested `AGENTS.md`): `adopt` classed every one as `nested`, linked nothing
(ADR-0046 links only agents and docs under `<home>/docs/modules/`), reported `22 proposed owner docs without an
existing doc`, and `apply` then wrote a skeleton `.agents/docs/modules/gateway.md` **and** appended the facts
block into `gateway/AGENTS.md` — two owner docs per module, one of them empty, on exactly the convention the
`agents-md` target (and with it M3h's `hermes` target) exists for.

## Decision

1. **Cover by path — decided by `plan`, reported by `adopt`.** A nested `AGENTS.md` whose directory is the
   `scope` of an `owner-doc`/`test-infra` entry covers it: `covered: gateway/AGENTS.md` is written on the plan
   entry and kept like a hand-written one (ADR-0046 — `merge_covers` carries it across re-plans while the file
   exists, drops it named when it vanishes). `plan` sets it from the same inventory `adopt` reads, so `plan →
   apply` without an `adopt` in between renders no skeleton either (the first cut set it in `adopt` only, and
   the quick-start order still produced the double doc). The file itself stays **unrecorded**, so `apply`
   still appends its facts block into it (ADR-0016); the row says so: `covers owner-doc gateway (the unit's own
   path) — apply appends its facts block` — with the `claude` target only there is no facts block for
   `AGENTS.md`, the nested `CLAUDE.md` carries the facts, and the row says that instead.
2. **Precedence: the plan's word, then the path, then the heuristic.** An entry with a `covered:` or a
   `decision:` is never touched by the rule. Where the path rule covers an entry, a file that the heuristic or
   the at-sherpa's-path rule would have linked is recorded as yours with the entry cleared, the row names the
   cover — `at sherpa's path, yours — gateway/AGENTS.md covers it (the unit's own path)` — and no *no unit
   matches* gap is raised for it (the row already said why).
3. **Three exclusions — and the one fact they rest on.** The team's doc is a file with **prose of its own
   outside sherpa's markers**: before `apply` appended its facts block and after, so the cover is the same fact
   on every run, and a lost `.sherpa/` rebuilds it from the files (ADR-0017 — the first cut excluded every file
   with markers, which made the cover unrecoverable after the first `apply` and let the second `adopt` re-link
   the files the first had demoted). Excluded: the root `AGENTS.md`, the harness index; a nested `CLAUDE.md`,
   runtime-specific (with `agents-md` on it is a one-line import stub); a file that is nothing but sherpa's
   block, sherpa's own proximity file — a team that wants *that* file to be the owner doc writes prose into it,
   or `covered:` by hand (ADR-0046).
4. **`apply` needs no new rule.** A covered entry is not selected, so no skeleton is rendered; the unit stays in
   the proximity list, so the facts block lands in the unit's own file as before; agents and librarians point
   at the covered path (ADR-0007 mechanics). One rendering change: when the covered path is the file being
   rendered, the proximity block drops its *Read the owner doc …* line — a pointer to itself. A skeleton an
   earlier `apply` wrote is taken back by the ADR-0048 removal when it is still sherpa's bytes.
5. **The agent seed stops carrying the doc path.** The seeded *Role* line named the owner-doc path in static
   prose outside the markers — a fact a cover changes, frozen in the one place `apply` never rewrites; removing
   a covered unit's skeleton would have dead-linked every generated agent (C4 FAIL, rollback). The line now
   points at the knowledge manifest (a block, regenerated). Agents written by sherpa ≤ 0.7.7 carry the old line
   outside the markers: it is an older rendering like an older stamp (ADR-0022) — `adopt` recognises the file as
   sherpa's whole through it, and `apply` refreshes the seed (`seed refreshed`) instead of leaving a file that
   the uninstall could only cut blocks out of (ADR-0048).

## Consequences

- Measured on the corpus repository from F39: `adopt` covers 9 entries by path, the gap count drops 22 → 13,
  `apply --dry-run` drops 38 → 29 files to add (nine skeletons less), the ten appended facts blocks unchanged.
- The heuristic (ADR-0046) keeps its field: owner docs that are *not* at their unit's path — named by
  abbreviation, living under `docs/modules/` — still link or stay the team's line in the plan, by design.
- A cover locks in only where the file is the unit's own; a team that already ran `apply` without `adopt` and
  got skeletons next to its `AGENTS.md` files gets out with one `covered:` per entry — the removal takes the
  skeleton back and the facts block stays in their file.
- The rule is idempotent: an entry already covered by its own `AGENTS.md` is returned again on every run — with
  the markers `apply` appended, too — so the demotion of heuristic links, the gap count and the rows hold on the
  second `adopt` as on the first, and the state never re-links a demoted file to the entry. `plan`, `adopt` and
  `apply` read one fact from one place: `covered:` on the entry, set by one function (`mark_covered`) with one
  precedence — the plan's word, the path, the state's link.
- A cover the state does not carry (by path, or by hand outside the harness homes) is no longer counted as a
  *proposed owner doc without an existing doc* — that gap reads `covered:` too.
- Regression risk watched: the rule fires on path equality only; on the corpus repositories without nested
  files at unit paths nothing changed (0 covers on two, one nested file not at a unit path on the third).

## Alternatives considered

- **Link `nested` files in the heuristic (name/mentions).** Rejected — that is the F35 heuristic on a second
  location: guesses, ties, ambiguity. The path is exact.
- **Record the covering file as `adopted`.** Rejected — adopted files are never touched (ADR-0007), so the
  facts block would never land in the one file every runtime reads first; unrecorded-plus-append is the
  ADR-0016 composition.
- **Render the full owner-doc facts table into the covering file.** Rejected — the nested file is injected
  whole by some runtimes and C7 budgets it at 8 KiB (ADR-0029); the short facts block is the right content
  there, and the team's prose stays the doc.
