# ADR-0041 — Architecture diagrams as Mermaid text under `docs/architecture/`

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei · **Decides:** plan Q25, the documentation half
(the per-unit graph rendered into the harness stays M3g)

## Context

Sherpa's mechanics — the pipeline, ownership per file, the write path, recovery — live in concept pages, command
pages and forty ADRs. Correct, but nobody sees the whole machine at once; the review rounds of this week showed
how much of the discussion was re-deriving how the pieces fit. A picture per mechanism is the missing view. The
constraints: no binaries in the repository, nothing that needs a tool to read, synced into the Obsidian vault,
never a CI cost.

## Decision

1. `docs/architecture/NN-<mechanism>.md`, one page per mechanism, Mermaid in fenced blocks, prose limited to
   "what to remember" — three or four bullets that name the invariant the picture shows. A `README.md` indexes
   the pages and names the owner of each mechanism; a page is a second view and never the owner of a rule.
2. Mermaid, as recommended in Q25: MIT, rendered by GitHub, Obsidian and MkDocs without a tool, readable by an
   agent as text, diffable. No Graphviz, PlantUML, D2, no rendered PNG/SVG.
3. `scripts/sync-kb.py` projects the folder as note type `architecture`, between concepts and reference.
4. CI: `docs/**` is in `paths-ignore` (ADR-0043), so a diagram change runs nothing. Locally,
   `tests/test_architecture_docs.py` (stdlib) keeps every fence a known diagram type, refuses `;` inside a
   sequence message (a statement separator in Mermaid — the one syntax trap hit while writing these), and
   checks that every ADR number and relative link resolves and that the index lists every page. Rendering is
   verified in a browser before a change is committed; no Node in the toolchain.

## Reasoning

- A diagram that lies is worse than none; tying each page to its owner and checking its references keeps the
  drift visible where it starts.
- The vault is where the diagrams are read (Obsidian renders Mermaid inline); the repository is where they are
  reviewed (GitHub renders them in the diff view).

## Consequences

- Eight pages at the start: pipeline, scan and model, plan entries, ownership, write path, state and recovery,
  outcome hook, runtimes. A new mechanism or a changed ADR that touches one updates the page in the same PR.
- M3g (the generated per-unit graph in the owner doc) reuses the format and the "one block of its own" rule.
