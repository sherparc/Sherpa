# Sherpa documentation

Sherpa turns a git repository into an AI harness in three deterministic steps — the way Terraform turns a
configuration into infrastructure: **scan** measures the codebase, **plan** proposes what the harness should
contain and why, **apply** creates exactly the approved part and keeps it current. `status` and `check` tell you
when the two have drifted apart.

```
sherpa scan   ──►  .sherpa/codebase-model.json   what the repo is: modules, churn, hotspots, dependencies, generators
sherpa plan   ──►  .sherpa/harness-plan.yaml     what the harness should contain: proposals and reasoned no's with evidence
sherpa apply  ──►  .agents/** · .claude/** · AGENTS.md · CLAUDE.md + .sherpa/state.json   the approved harness
sherpa adopt  ──►  .sherpa/state.json                an existing harness taken over unchanged; a lost state rebuilt from the files
sherpa status ──►  drift, checker findings, outcome labels per harness version
sherpa check  ──►  structural rules C1–C8 for the harness files (also runs without sherpa installed)
sherpa doctor ──►  every prerequisite with a fix; sherpa self-update installs the next release
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
| `sherpa apply` | dry run, then the harness files (neutral core under `.agents/` or `.claude/`, projections for Claude Code and the AGENTS.md family) and the state; managed blocks; outcome hook | [commands/apply.md](commands/apply.md) |
| `sherpa adopt` | take an existing harness into the state without changing a byte; rebuild a lost state; cover plan entries that files already fill | [commands/adopt.md](commands/adopt.md) |
| `sherpa status` | drift between state, files and plan; checker; outcome labels | [commands/status.md](commands/status.md) |
| `sherpa check` | structural rules C1–C8, standalone copy in the repo | [commands/check.md](commands/check.md) |
| `sherpa doctor` | every prerequisite (Python, git, origin, trunk, config, runtime, install, update) with a fix | [commands/doctor.md](commands/doctor.md) |
| `sherpa self-update` | the latest GitHub release via the installer that owns this copy; the daily hint | [commands/self-update.md](commands/self-update.md) |

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
- [Apply](concepts/harness-apply.md) — what each entry becomes, ownership modes, state, outcome hook, checker rules,
  adopt and the rebuildable state.

## Architecture diagrams

- [Diagrams](architecture/README.md) — the mechanics as Mermaid: the pipeline, scan and model, plan entries,
  ownership per file, the write path, state and recovery, the outcome hook, runtimes. A second view; each one
  links to the page that owns the rule.

## Project

- [Plan and roadmap](plan.md) — architecture, milestones, open questions, what is deliberately not built.
- [Architecture decision records](adr/README.md) — one file per decision; what has no ADR is not decided.
