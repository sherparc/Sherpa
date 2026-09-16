# `sherpa status`

One screen for "is the harness still what Sherpa last wrote, and does it work?": drift between the state, the
files and the plan; the checker's findings; the outcome labels per harness version. Read-only.

## Synopsis

```
sherpa status [REPO]
```

## What it does

1. Loads `.sherpa/state.json` (an empty state when there is none), `.sherpa/harness-plan.yaml` and
   `.sherpa/codebase-model.json`.
2. Renders what [`sherpa apply`](apply.md) would do now — the same pure comparison, nothing written.
3. Runs the checker rules C1–C7 ([`sherpa check`](check.md)); C8 (drift) is replaced by the sharper per-block
   view above.
4. Counts the labels in `.sherpa/telemetry/outcomes.ndjson` per `harness_rev`.
5. Notes when the deployed checker copy is older than the installed sherpa.

## Output

```console
$ sherpa status .
sherpa status — harness_rev 5be9c857fd4b, applied 2026-09-16T22:07:12Z
drift: 4 files
  ? .claude/agents/old.md            in the state, no longer in the plan
  - .claude/docs/modules/web.md      in the state, not on disk — apply recreates it
  ! .claude/hooks/sherpa-outcome.py  hand-edited (skipped)
  ~ .claude/docs/modules/pay.md      block facts updated
check: 0 FAIL, 1 WARN
  WARN C7 .claude/agents/pay.md: 162 lines > budget 150 (agent)
outcomes: 3 executions labelled, 1 corrections
  5be9c857fd4b (current): 1 success, 0 failed, 1 unknown
  000000000000: 0 success, 1 failed, 0 unknown
  note: .claude/scripts/sherpa-check.py is sherpa 0.0.1, installed is 0.4.0 — `sherpa apply` refreshes it
```

Without drift the second line reads `drift: none — files match the state and the plan`; without labels,
`outcomes: none yet — labels appear once Claude Code runs with the hook installed`.

### Drift lines

| Mark | Meaning | What to do |
|---|---|---|
| `+` | a file the plan wants that does not exist yet | `sherpa apply` |
| `~` | a block or managed file whose content is behind the model (a rescan changed the facts, a new sherpa version) | `sherpa apply` |
| `!` | a hand-edited block or file, broken markers, or a file sherpa does not manage | nothing — it is yours; `apply` skips it too |
| `-` | in the state, not on disk | `sherpa apply` recreates it, or remove the record if the deletion was intended |
| `?` | orphan: in the state, no longer in the plan (the entry was rejected or the module disappeared) | delete the file and its state record by hand — Sherpa never deletes |

### Outcomes

One line per `harness_rev` seen in the labels, the current one first and marked. `success` = the last test run
in the execution was green or a pull request was created; `failed` = the last test run was red; `unknown` = no
signal, typically a question/answer turn. `corrections` counts follow-up prompts that corrected the previous
answer. Trend, regression between two harness versions and the share of `unknown` over time are milestone M5.

## Exit codes

| Exit | When |
|---|---|
| 0 | no checker FAIL — drift, warnings and orphans are informational |
| 1 | at least one checker FAIL (C1–C6), or plan/model missing (`… not found — run `sherpa plan` first`) |

## Typical uses

- **Before a commit**: `sherpa status` — drift `none`, `0 FAIL`.
- **After a merge**: `sherpa plan && sherpa status` — the `~` lines show which facts blocks a rescan changed.
- **In CI**: `sherpa status` as a gate for the checker (exit 1 on FAIL); drift does not fail the build, because
  hand edits are legitimate.
- **After a sherpa upgrade**: the note about the checker copy tells you to run `sherpa apply` once.

## See also

[`sherpa apply`](apply.md) · [`sherpa check`](check.md) ·
[concepts/harness-apply.md](../concepts/harness-apply.md#sherpa-status) · ADR-0013.
