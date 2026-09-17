# Architecture diagrams

> Owner of: nothing. Every diagram here is a second view of a mechanism that a concept page, a command page or
> an ADR owns; each one links to its owner. Mermaid as text (ADR-0041): GitHub, Obsidian (`kb-sherpa/`) and MkDocs
> render it, an agent reads it as plain text, no tool in the repository. `docs/**` never triggers CI; a small
> stdlib test keeps the fences well-formed and the references alive.

| # | Diagram | The mechanism | Owner |
|---|---|---|---|
| 00 | [pipeline](00-pipeline.md) | scan → model → plan → apply → state, and who owns which file | [concepts/harness-apply](../concepts/harness-apply.md), [plan §2](../plan.md) |
| 01 | [scan and model](01-scan-model.md) | T0 Git and T1 manifests to modules, hotspots and change coupling | [concepts/scan](../concepts/scan.md) |
| 02 | [plan entries](02-plan-rules.md) | the life of an entry: default, decision, covered, selected | [concepts/harness-plan](../concepts/harness-plan.md) |
| 03 | [ownership](03-ownership.md) | the decision per file when `apply` meets what is on disk | [commands/apply](../commands/apply.md), ADR-0013, 0016, 0033 |
| 04 | [write path](04-write-path.md) | preview, confirmation, compare-and-swap, atomic writes, rollback | ADR-0030, 0031, 0032 |
| 05 | [state and recovery](05-state-and-recovery.md) | the index, a torn state, a stale plan, who refuses what | ADR-0017, 0019, 0034 |
| 06 | [outcome hook](06-outcome-hook.md) | events to signals to one label per execution | [commands/apply — the outcome hook](../commands/apply.md#the-outcome-hook), ADR-0008, 0040 |
| 07 | [runtimes](07-runtimes.md) | the neutral core under `home` and one adapter per runtime | ADR-0015, 0023 |

Reading order for a newcomer: 00, 07, 02, 03, 04, 05 — then 01 and 06 as the two ends of the loop (what goes in,
what comes back).
