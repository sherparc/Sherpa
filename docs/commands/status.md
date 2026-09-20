# `sherpa status`

One screen for "is the harness still what Sherpa last wrote, and does it work?": drift between the state, the
files and the plan; the checker's findings; the outcome labels per harness version. Read-only.

## Synopsis

```
sherpa status [REPO] [--json]
```

## What it does

1. Loads `.sherpa/state.json` (an empty state when there is none), `.sherpa/harness-plan.yaml` and
   `.sherpa/codebase-model.json`; notes whether the trunk moved since the plan was made (`plan: stale`).
2. Renders what [`sherpa apply`](apply.md) would do now — the same pure comparison, nothing written.
3. Runs the checker rules C1–C7 ([`sherpa check`](check.md)) — C1–C5 FAIL only in files sherpa generated,
   WARN `(yours)` in adopted and unrecorded ones (ADR-0047); C8 (drift) is replaced by the sharper per-block
   view above.
4. Counts the labels in `.sherpa/telemetry/outcomes.ndjson` per `harness_rev`.
5. Notes when the deployed checker copy is older than the installed sherpa.

## Output

```console
$ sherpa status .
sherpa status — harness_rev c38498363846, applied 2026-09-16T22:07:12Z
plan: current
drift: 4 files
  ? .claude/agents/old.md            no longer in the plan — `apply` removes it
  - .agents/docs/modules/core.md     in the state, not on disk — apply recreates it
  ! .claude/hooks/sherpa-outcome.py  hand-edited (skipped)
  ~ .agents/docs/modules/pay.md      block facts updated
check: 0 FAIL, 1 WARN
  WARN C7 .claude/agents/pay.md: 162 lines > budget 150 (agent)
outcomes: 3 executions labelled, 1 corrections
  c38498363846 (current): 1 success, 0 failed, 1 unknown
  000000000000: 0 success, 1 failed, 0 unknown
  note: .agents/scripts/sherpa-check.py is sherpa 0.0.1, installed is 0.4.0 — `sherpa apply` refreshes it
```

Without drift the drift line reads `drift: none — files match the state and the plan`; without labels,
`outcomes: none yet — labels appear once Claude Code runs with the hook installed`.

The `plan:` line is what `apply` checks first: when the trunk moved since `sherpa plan` it reads
`plan: stale — origin/main moved 2c22d796e3 → 9bac74de60 since \`sherpa plan\`; run \`sherpa plan\`` — a
warning, never an exit code. The harness can be current while the plan is stale (ADR-0019: a merge without
activity in a unit changes no block), so the two facts are two lines.

A torn or foreign `.sherpa/state.json` gets its own line and makes drift unknown rather than wrong (ADR-0034):

```
state: unreadable — .sherpa/state.json is unreadable (state has schema_version 2, expected 1) — `sherpa adopt` rebuilds it from the harness files
drift: unknown until the state is rebuilt
```

`--json` prints the same report for scripts:

```json
{
  "sherpa": "0.7.4",
  "harness_rev": "c38498363846",
  "applied_at": "2026-09-16T22:07:12Z",
  "plan": {"stale": true, "trunk": "origin/main", "plan_rev": "2c22d796e3…", "current_rev": "9bac74de60…"},
  "state": {"error": null},
  "drift": [{"op": "~", "path": ".agents/docs/modules/pay.md", "detail": "block facts updated"}],
  "findings": [{"level": "WARN", "rule": "C7", "path": ".claude/agents/pay.md", "message": "162 lines > budget 150 (agent)"}],
  "outcomes": {"c38498363846": {"success": 1, "unknown": 1}},
  "corrections": 1,
  "notes": []
}
```

### Drift lines

| Mark | Meaning | What to do |
|---|---|---|
| `+` | a file the plan wants that does not exist yet | `sherpa apply` |
| `~` | a block or managed file whose content is behind the model (a rescan changed the facts, a new sherpa version) | `sherpa apply` |
| `!` | a hand-edited block or file, broken markers, or a file sherpa does not manage | nothing — it is yours; `apply` skips it too |
| `-` | in the state, not on disk | `sherpa apply` recreates it when the plan still wants it; when it does not (a rejected entry, a deleted file) the line says `apply` drops the record |
| `?` | no longer in the plan (the entry was rejected or the module disappeared) — the line says what `apply` does: `removes it`, `removes sherpa's blocks from it`, or `drops the record, the file is yours` when it was changed by hand (ADR-0048) | `sherpa apply` |

Files recorded as `origin: adopted` ([`sherpa adopt`](adopt.md)) never appear as drift — a hand edit to them is
the intended state of affairs; only a deleted one is listed (`-`) until the next `adopt` drops the record. A
note counts them: `note: 6 adopted files are yours and never touched (ADR-0007)`. When both `.agents/` and
`.claude/` exist and nothing decides where the core lives, `status` — like every preview — assumes `.agents`
and says so in a note first (ADR-0036); the drift below it is what `apply` would do under that assumption.

### Outcomes

One line per `harness_rev` seen in the labels: the current one first and marked, then the five most recent revisions by their first label, newest first, and `and N older revisions — sherpa status --json lists them all` for the rest (`--json` carries every revision). `success` = the last test run
in the execution was green or a pull request was created; `failed` = the last test run was red; `unknown` = no
signal, typically a question/answer turn. `corrections` counts follow-up prompts that corrected the previous
answer. Trend, regression between two harness versions and the share of `unknown` over time are milestone M5.

## Exit codes

| Exit | When |
|---|---|
| 0 | no checker FAIL — drift, warnings and orphans are informational |
| 1 | at least one checker FAIL (C1–C6, in a file sherpa generated), or plan/model missing (`… not found — run `sherpa plan` first`) |

A torn or foreign `.sherpa/state.json` does not stop the report: the `state:` line names it with the way out
(also on stderr, and as `"state": {"error": …}` in JSON), drift is `unknown` and the checker still runs (ADR-0034).

## Typical uses

- **Before a commit**: `sherpa status` — drift `none`, `0 FAIL`.
- **After a merge**: `sherpa plan && sherpa status` — the `~` lines show which facts blocks a rescan changed.
- **In CI**: `sherpa status` as a gate for the checker (exit 1 on FAIL); drift does not fail the build, because
  hand edits are legitimate.
- **After a sherpa upgrade**: the note about the checker copy tells you to run `sherpa apply` once.

## See also

[`sherpa apply`](apply.md) · [`sherpa check`](check.md) ·
[concepts/harness-apply.md](../concepts/harness-apply.md#sherpa-status) · ADR-0013.
