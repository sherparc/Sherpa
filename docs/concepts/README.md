# How Sherpa thinks

The command pages say what each command does; these documents own the rules behind them and the reasoning for
every decision — with the numbers that calibrated them. Six principles run through all three:

1. **Every number is a measurement.** The plan cites model fields only — commits, authors, files, dependents,
   ranks — never an estimate. What cannot be measured is not proposed.
2. **Trunk discipline.** Everything is measured on `origin/<trunk>`; the checked-out branch and the working tree
   do not exist for Sherpa. Same commit, same result, weeks later.
3. **One owner per fact.** The owner doc holds the facts of a module; agents carry a role and a manifest and point
   there; skills are procedures. A sentence written in two places is wrong as soon as one of them changes.
4. **Generated code is regenerated, not explained** (ADR-0011). A migrations project gets a skill with sources,
   config and command, not an agent that explains its output.
5. **The no is as valuable as the yes.** Every proposal that is not made and is within reach is listed with the
   criterion that would flip it; dormant modules are named; nothing disappears silently (ADR-0012).
6. **Dry run first, blocks not files** (ADR-0008, ADR-0013). Nothing is written before you have seen the list;
   afterwards Sherpa owns only marked blocks inside the files and an outcome signal is in place from day one.

| Document | Owns |
|---|---|
| [scan.md](scan.md) | layers T0 (git) and T1 (modules), generator families, twelve measurement decisions |
| [harness-plan.md](harness-plan.md) | units, rank and floor, reach, dormant and generator-dominated units, the YAML format, decision keeping |
| [harness-apply.md](harness-apply.md) | what every entry becomes, ownership modes, the state and `harness_rev`, the outcome hook, the checker rules |

Decisions with their context and consequences: [../adr/README.md](../adr/README.md). Milestones and open
questions: [../plan.md](../plan.md).
