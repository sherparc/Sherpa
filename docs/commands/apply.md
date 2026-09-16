# `sherpa apply`

Create the approved part of the plan under `.claude/` and record it in `.sherpa/state.json`. Dry run first:
every file is listed with what would happen to it before anything is written. Idempotent: the second run in a row
does nothing. Sherpa owns marked blocks inside the files, not the files — your text stays.

## Synopsis

```
sherpa apply [REPO] [--yes | -y] [--dry-run] [--no-check]
```

## What it does

1. Loads `REPO/.sherpa/harness-plan.yaml` and `REPO/.sherpa/codebase-model.json`; refuses when `origin/<trunk>`
   has moved since the plan was made (a saved plan is stale — run [`sherpa plan`](plan.md) again).
2. Selects the entries: every `default: propose` without `decision: reject`, every `default: skip` with
   `decision: accept`. A rejected `outcome` entry is an error.
3. Renders the target files from the plan and the model (pure, no clock) and compares them with the files on disk
   and the state — one action per file: `+ new`, `~ updated`, `= unchanged`, `! skipped`.
4. Prints the list. Stops here with `--dry-run`, or when there is nothing to write, or when there is no terminal
   to ask; otherwise asks `apply? [y/N]` (skipped with `--yes`).
5. Runs the checker ([`sherpa check`](check.md)) before and after writing. A write that introduces a **new** FAIL
   is rolled back completely; pre-existing FAILs are reported and do not block.
6. Writes `.sherpa/state.json` with one record per file, `harness_rev` and `applied_at`.

Ownership modes, file contents and the reasoning: [concepts/harness-apply.md](../concepts/harness-apply.md).

## Options

| Option | Default | Effect |
|---|---|---|
| `REPO` | `.` | repository root |
| `--yes`, `-y` | ask | write without the question (CI, scripts) |
| `--dry-run` | ask | list only; never asks, never writes |
| `--no-check` | check | skip the checker after writing — no rollback. For repositories whose hand-written harness has FAILs you want to fix later; the FAILs are still reported by `sherpa status`. |

Without a terminal on stdin and without `--yes`, `apply` prints the list and
`dry run only — pass --yes to write (no terminal to ask).` — dry run is the default everywhere (ADR-0008).

## What is created

| Plan entry | File(s) | Sherpa's part (regenerated on every apply) |
|---|---|---|
| always | `CLAUDE.md` | block `harness` — six lines on where facts, agents and skills live; appended to an existing file; a new file imports an existing `AGENTS.md` (`@AGENTS.md`) |
| always | `.claude/scripts/sherpa-check.py` | whole file — the checker, runs without sherpa installed |
| `outcome` | `.claude/hooks/sherpa-outcome.py`, hook entries in `.claude/settings.json`, `.sherpa/telemetry/.gitignore` | the script; sherpa's four hook entries (everything else in `settings.json` is kept) |
| `owner-doc`, `test-infra` | `.claude/docs/modules/<slug>.md` | block `facts`: path, kind, files/LOC, commits, authors, dependencies, dependents, tests, hotspots, generators |
| `agent` | `.claude/agents/<slug>.md` | block `knowledge` (front matter manifest) and block `manifest` |
| `librarian` | `.claude/skills/<slug>-sync/SKILL.md` | block `scope`: pathspec, commits/30d, cadence, owner doc |
| `skill` | `.claude/skills/regenerate-<family>/SKILL.md` | block `facts`: family, home, generated files, sources, configs, command |

Slugs are lower-case `[a-z0-9-]` from the unit id (`Shop.Pricing` → `shop-pricing`); two units with the same
slug get the scope appended. Everything outside a block — the agent's `description`, the owner doc's
`structure`, `rules`, `key services`, `references` sections, the skill's procedure — is seeded once and then
yours.

## Output

Dry run on the five-module example repository (golden
[`active-apply-console.txt`](../../tests/goldens/active-apply-console.txt)):

```console
$ sherpa apply .
sherpa apply — plan origin/main@5db69c4ddd: 10 entries, 6 selected → 11 files
  + .claude/agents/pay.md                                 agent pay                     new
  + .claude/docs/modules/core.md                          owner-doc core                new
  + .claude/docs/modules/pay.md                           owner-doc pay                 new
  + .claude/docs/modules/suite.md                         test-infra suite              new
  + .claude/docs/modules/web.md                           owner-doc web                 new
  + .claude/hooks/sherpa-outcome.py                       harness                       new
  + .claude/scripts/sherpa-check.py                       harness                       new
  + .claude/settings.json                                 harness                       new
  + .claude/skills/regenerate-django-migrations/SKILL.md  skill regenerate-django-migrations  new
  + .sherpa/telemetry/.gitignore                          harness                       new
  + CLAUDE.md                                             harness                       new
11 to add, 0 to change, 0 unchanged, 0 skipped.
apply? [y/N] y
check: 0 FAIL, 0 WARN
11 files written · harness_rev 5be9c857fd4b → .sherpa/state.json
```

Columns: action, path, the plan entry (`kind target`, or `harness` for the always-part), detail. The detail
lines and what each means:

| Detail | Meaning |
|---|---|
| `new` | file does not exist; written from the seed |
| `updated` | managed file (a sherpa script) changed with the sherpa version |
| `block facts updated` | only that block is rewritten; the rest of the file is untouched |
| `block facts updated; block manifest hand-edited` | one block regenerated, the other left alone |
| `block harness appended` | `CLAUDE.md` existed without markers — the block is appended at the end |
| `hooks added: UserPromptSubmit, PostToolUse, PostToolUseFailure, Stop` | `settings.json` existed — sherpa's hook entries merged in |
| `unchanged` / `hooks present` | nothing to do |
| `hand-edited (skipped)` | managed file whose hash differs from the state — sherpa never overwrites it |
| `block facts hand-edited (skipped)` | the block's content differs from what sherpa last wrote — it is yours now; `status` keeps showing it |
| `block facts removed by hand (skipped)` | you deleted the markers; sherpa does not put them back |
| `markers broken: block facts is never closed (skipped)` | fix the markers by hand (`sherpa check` C5 names the line) |
| `exists, not managed by sherpa — sherpa adopt takes it over` | a file at that path without a state record — an existing harness; nothing is touched |

After the write: the checker summary, then `N files written · harness_rev <12 hex> → .sherpa/state.json`. On
a rollback: `check: 1 new FAIL — rolled back, nothing written` followed by the findings.

## The state and `harness_rev`

`.sherpa/state.json` records, per file, the ownership mode (`managed`, `blocks`, `json-hooks`), the origin
(`generated`; `adopted` once `sherpa adopt` exists), the plan entry and the hashes sherpa wrote — one per managed
file, one per block. `harness_rev` is a hash over all of them plus the sherpa version: it changes exactly when
sherpa's share of the harness changes. The outcome hook stamps it on every label, so `sherpa status` can compare
harness versions. `applied_at` is the only timestamp Sherpa ever writes and lives only here. Commit the state
(ADR-0005). Schema: [`harness-state.schema.json`](../../src/sherpa/schemas/harness-state.schema.json).

## The outcome hook

Installed with every apply (ADR-0008): `.claude/hooks/sherpa-outcome.py`, wired in `.claude/settings.json` for
`UserPromptSubmit`, `PostToolUse` (`Bash|Edit|Write|MultiEdit`), `PostToolUseFailure` (`Bash`) and `Stop`.
It is stdlib-only, fail-open and never prints. Per execution it appends one line to
`.sherpa/telemetry/outcomes.ndjson` with a label — `success` (last test run green, or a PR created), `failed`
(last test run red), `unknown` (no signal) — the tool signals, and the `harness_rev`. A follow-up prompt that
starts with a correction ("no, that's wrong", "doesn't work", …) records a `correction` for the previous
execution. Telemetry is ignored by git through `.sherpa/telemetry/.gitignore`. Details:
[concepts/harness-apply.md](../concepts/harness-apply.md#outcome-minimum--the-hook-adr-0008).

The hook command is `sh -c '… python3 "$0" || python "$0"' "$CLAUDE_PROJECT_DIR/.claude/hooks/sherpa-outcome.py"`
— `python3` where it exists, `python` otherwise (Windows launchers).

## Exit codes and errors

| Exit | When | Message |
|---|---|---|
| 0 | dry run, aborted at the question, nothing to do, or written and checked | see output |
| 1 | no plan | `sherpa apply: /repo/.sherpa/harness-plan.yaml not found — run `sherpa plan` first` |
| 1 | no model | `sherpa apply: /repo/.sherpa/codebase-model.json not found — run `sherpa plan` first` |
| 1 | plan stale (trunk moved) | `sherpa apply: harness-plan.yaml is from origin/main@5db69c4ddd, origin/main is now at d8cc7bf4ec — run `sherpa plan` first` |
| 1 | plan and model disagree | `sherpa apply: harness-plan.yaml was made from 5db69c4ddd, the model is at d8cc7bf4ec — run `sherpa plan` first` |
| 1 | outcome rejected | `sherpa apply: the outcome entry is rejected — a harness without a signal is not created (ADR-0008)` |
| 1 | rolled back | `check: N new FAIL — rolled back, nothing written` + findings |
| 1 | plan file invalid | `sherpa apply: harness-plan.yaml invalid at …` |

## Determinism

`(plan, model, files, state) → actions` is a pure function; the only side effects are the writes. No clock in
any file (dates in the facts blocks are the model's `as_of`), no sherpa version in the blocks (an upgrade must
not rewrite every doc), sorted output, hashes with normalised line endings (a CRLF checkout is not a hand edit).
Proven by `test_apply_is_idempotent_and_deterministic`: the second run is all `=`, state and tree hash unchanged.
61 files for a 15k-file monorepo plan render and compare in 0.15 s.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Everything is `! exists, not managed by sherpa` | the repo already has a `.claude/` — those files have no state record | wait for `sherpa adopt` (M3c); until then rename or accept that they stay untouched |
| `status` shows `~ block facts updated` right after `apply` | `apply` was run with an older model than the plan | run `sherpa plan` then `sherpa apply` |
| CLAUDE.md got a block at the very end, below my own sections | intended — sherpa appends, never reorders | move the block; its markers are what matters, not its position |
| The hook writes nothing | `settings.json` entries missing (someone removed them) or no `python3`/`python` on the PATH | `sherpa apply` merges the entries back; `sherpa check` C6 verifies the wiring |
| I want sherpa to take a hand-edited block back | delete your changes inside the block, or remove the file's record from `.sherpa/state.json` | the next apply regenerates it |
| Rollback although my files are fine | the write introduced a FAIL — usually a link into a file the plan no longer creates | read the findings; `--no-check` writes anyway |

## See also

[`sherpa plan`](plan.md) · [`sherpa status`](status.md) · [`sherpa check`](check.md) ·
[concepts/harness-apply.md](../concepts/harness-apply.md) · ADR-0008 (dry run, outcome minimum), ADR-0013
(managed blocks, checker, selection).
