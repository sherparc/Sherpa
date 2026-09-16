# Sherpa documentation

Sherpa turns a git repository into an AI harness in three deterministic steps — the way Terraform turns a
configuration into infrastructure: **scan** measures the codebase, **plan** proposes what the harness should
contain and why, **apply** creates exactly the approved part and keeps it current. `status` and `check` tell you
when the two have drifted apart.

```
sherpa scan   ──►  .sherpa/codebase-model.json   what the repo is: modules, churn, hotspots, dependencies, generators
sherpa plan   ──►  .sherpa/harness-plan.yaml     what the harness should contain: proposals and reasoned no's with evidence
sherpa apply  ──►  .claude/** + .sherpa/state.json   the approved harness: owner docs, agents, skills, outcome hook
sherpa status ──►  drift, checker findings, outcome labels per harness version
sherpa check  ──►  structural rules for .claude/** (also runs without sherpa installed)
```

## Start here

- [Getting started](getting-started.md) — install, first run on your repo, what to look at, what to commit.
- [How Sherpa thinks](concepts/README.md) — the principles behind every proposal: evidence, one owner per fact,
  generated code is regenerated, dry run first, blocks instead of files.

## Command reference

One page per command: synopsis, every option, inputs and outputs, exit codes, real examples, troubleshooting.

| Command | Purpose | Page |
|---|---|---|
| `sherpa scan` | deterministic codebase model from `origin/<trunk>` | [commands/scan.md](commands/scan.md) |
| `sherpa plan` | proposals and reasoned no's with evidence; decisions survive a re-plan | [commands/plan.md](commands/plan.md) |
| `sherpa apply` | dry run, then files under `.claude/` and the state; managed blocks; outcome hook | [commands/apply.md](commands/apply.md) |
| `sherpa status` | drift between state, files and plan; checker; outcome labels | [commands/status.md](commands/status.md) |
| `sherpa check` | structural rules C1–C8, standalone copy in the repo | [commands/check.md](commands/check.md) |

Planned: `sherpa adopt` (take over an existing harness), `sherpa doctor` (environment check).

## Reference

- [Configuration — `sherpa.toml`](reference/configuration.md) — every key with default, meaning and effect.
- [Files, exit codes, environment](reference/files-and-exit-codes.md) — what Sherpa reads and writes, what to
  commit, what each exit code means.
- JSON schemas: [codebase-model](../src/sherpa/schemas/codebase-model.schema.json),
  [harness-plan](../src/sherpa/schemas/harness-plan.schema.json),
  [harness-state](../src/sherpa/schemas/harness-state.schema.json).

## Concepts — rules and formats in depth

- [Scan](concepts/scan.md) — layers T0 (git) and T1 (modules), generator families, twelve decisions and why.
- [Plan](concepts/harness-plan.md) — units, rank and floor, reach, dormant units, generator skills, YAML format.
- [Apply](concepts/harness-apply.md) — what each entry becomes, ownership modes, state, outcome hook, checker rules.

## Project

- [Plan and roadmap](plan.md) — architecture, milestones, open questions, what is deliberately not built.
- [Architecture decision records](adr/README.md) — one file per decision; what has no ADR is not decided.
