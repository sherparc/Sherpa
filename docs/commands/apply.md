# `sherpa apply`

Create the approved part of the plan and record it in `.sherpa/state.json`. Dry run first: every file is listed
with what would happen to it before anything is written. Idempotent: the second run in a row does nothing.
**Sherpa never overwrites what exists in your repository** (ADR-0016): it creates files, appends its blocks to
existing ones, merges hook entries, and rewrites only bytes it wrote itself that nobody changed since.

## Synopsis

```
sherpa apply [REPO] [--yes | -y] [--dry-run] [--no-check]
```

## What it does

1. Loads `REPO/.sherpa/harness-plan.yaml` and `REPO/.sherpa/codebase-model.json`; refuses when `origin/<trunk>`
   has moved since the plan was made (a saved plan is stale — run [`sherpa plan`](plan.md) again).
1. Resolves the layout (ADR-0015): `home` — where owner docs, skills and the checker copy live (`.agents`, the
   cross-tool default, or `.claude`) — and the `targets` to project into (`claude`, `agents-md`). Both come
   from `sherpa.toml [apply]`, else from the state, else from the repository: exactly one of `.claude/` and
   `.agents/` present → that one; **both present → `apply` asks** (and refuses without a terminal); **neither →
   `apply` asks, `.agents` is the default** (Enter, `--yes`, `--dry-run` or no terminal take it). The first
   output line says what was resolved: `targets: claude, agents-md · home: .agents`.
2. Selects the entries: every `default: propose` without `decision: reject`, every `default: skip` with
   `decision: accept`. A rejected `outcome` entry is an error.
3. Renders the target files from the plan and the model (pure, no clock) and compares them with the files on disk
   and the state — one action per file: `+ new`, `~ updated`, `= unchanged`, `! skipped`.
4. Prints the list. Stops here with `--dry-run`, or when there is nothing to write, or when there is no terminal
   to ask; otherwise asks `apply? [y/N]` (skipped with `--yes`).
5. Re-reads every file it is about to write and skips one that changed since the preview — an editor, a second
   agent (ADR-0030); a path with a symlink in it is never written through (ADR-0031). Each file is written
   whole or not at all, and a write error half-way rolls back what was written (ADR-0032). Runs the checker
   ([`sherpa check`](check.md)) before and after writing. A write that introduces a **new** FAIL is rolled back
   completely; pre-existing FAILs are reported and do not block.
6. Writes `.sherpa/state.json` with one record per file, `harness_rev` and `applied_at`.

Ownership modes, file contents and the reasoning: [concepts/harness-apply.md](../concepts/harness-apply.md).

## Options

| Option | Default | Effect |
|---|---|---|
| `REPO` | `.` | repository root |
| `--yes`, `-y` | ask | write without the question (CI, scripts) |
| `--dry-run` | ask | list only; never asks, never writes |
| `--no-check` | check | skip the checker after writing — no rollback. For repositories whose hand-written harness has FAILs you want to fix later; the FAILs are still reported by `sherpa status`. |

`home` and `targets` have no flags: set them in `sherpa.toml [apply]` ([configuration](../reference/configuration.md#apply)) — a layout is a decision, not a per-run option.

Without a terminal on stdin and without `--yes`, `apply` prints the list and
`dry run only — pass --yes to write (no terminal to ask).` — dry run is the default everywhere (ADR-0008).

## What is created

The neutral core (under `home`), then one adapter per target. Sherpa's part of every file is regenerated on each
apply; everything else is seeded once and yours.

| Plan entry | Core (`<home>/…`) | Target `claude` | Target `agents-md` |
|---|---|---|---|
| always | `scripts/sherpa-check.py` (the checker copy), `.sherpa/telemetry/.gitignore` | `CLAUDE.md` block `harness` (appended to an existing file; a new file imports `@AGENTS.md` when that exists or is generated) | `AGENTS.md` block `harness`: overview and the index of nested files — the 20 most active units by name, the rest counted (the root file is loaded on every turn); the facts of a root module |
| `outcome` | — | `.claude/hooks/sherpa-outcome.py`, four hook entries merged into `.claude/settings.json` | — (no hooks in this family; `apply` says so when `claude` is off) |
| `owner-doc`, `test-infra` | `docs/modules/<slug>.md` block `facts`: path, kind, files/LOC, commits, authors, dependencies, dependents, tests, hotspots, change coupling, generators; a module with sub-units (ADR-0020) adds `contains` with links and says how many files are described there; a sub-unit gets its own hotspots and the test files naming it | `<unit>/CLAUDE.md` block `harness`: `@AGENTS.md` when both targets are on, else the facts inline | `<unit>/AGENTS.md` block `facts`: dependencies, dependents, tests, hotspots, generated code → skill, link to the owner doc |
| `agent` | — | `.claude/agents/<slug>.md` blocks `knowledge` (front matter manifest pointing at the owner doc and skills) and `manifest` | — |
| `librarian` | `skills/<slug>-sync/SKILL.md` block `scope` | stub `.claude/skills/<slug>-sync/SKILL.md` when `home` is `.agents` | — |
| `skill` | `skills/regenerate-<family>/SKILL.md` block `facts` | stub `.claude/skills/regenerate-<family>/SKILL.md` when `home` is `.agents` | — |

Nested `AGENTS.md`/`CLAUDE.md` are **proximity files**: a runtime working in `svc/pay/` loads them without any
manifest (the closest file wins). Their blocks are projections of the same model as the owner doc's facts block;
the owner doc stays the place for detail and human text. A stub is a managed file with the skill's front matter
and a link — Claude Code lists the skill, the procedure has one owner.

Slugs are lower-case `[a-z0-9-]` from the unit id (`Shop.Pricing` → `shop-pricing`); two units with the same
slug get the scope appended. Everything outside a block — the agent's `description`, the owner doc's
`structure`, `rules`, `key services`, `references` sections, the skill's procedure — is seeded once and then
yours.

## Output

Dry run on the five-module example repository (golden
[`active-apply-console.txt`](../../tests/goldens/active-apply-console.txt)):

```console
$ sherpa apply .
targets: claude, agents-md · home: .agents
sherpa apply — plan origin/main@5db69c4ddd: 10 entries, 5 selected → 18 files
  + .agents/docs/modules/core.md                          owner-doc core                new
  + .agents/docs/modules/pay.md                           owner-doc pay                 new
  + .agents/docs/modules/suite.md                         test-infra suite              new
  + .agents/scripts/sherpa-check.py                       harness                       new
  + .agents/skills/regenerate-django-migrations/SKILL.md  skill regenerate-django-migrations  new
  + .claude/agents/pay.md                                 agent pay                     new
  + .claude/hooks/sherpa-outcome.py                       harness                       new
  + .claude/settings.json                                 harness                       new
  + .claude/skills/regenerate-django-migrations/SKILL.md  skill regenerate-django-migrations  new
  + .sherpa/telemetry/.gitignore                          harness                       new
  + AGENTS.md                                             harness                       new
  + CLAUDE.md                                             harness                       new
  + svc/core/AGENTS.md                                    owner-doc core                new
  + svc/core/CLAUDE.md                                    owner-doc core                new
  + svc/pay/AGENTS.md                                     owner-doc pay                 new
  + svc/pay/CLAUDE.md                                     owner-doc pay                 new
  + tests/suite/AGENTS.md                                 test-infra suite              new
  + tests/suite/CLAUDE.md                                 test-infra suite              new
18 to add, 0 to change, 0 unchanged, 0 skipped.
apply? [y/N] y
check: 0 FAIL, 0 WARN
18 files written · harness_rev c38498363846 → .sherpa/state.json
```

The first line is the resolved layout; columns: action, path, the plan entry (`kind target`, or `harness` for
the always-part), detail. The detail lines and what each means:

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
| `adopted — yours, never touched (skipped)` | recorded as `origin: adopted` by [`sherpa adopt`](adopt.md); only shown when a plan entry was accepted on top of it |
| `exists with sherpa markers but no state record — sherpa adopt` | markers but no record (deleted state, copied file): treated as yours (ADR-0016) |
| `block facts not written by sherpa (skipped)` | a block with Sherpa's name that Sherpa never wrote — yours |
| `changed since the preview (skipped)` | the file moved between the preview and your `y` — nothing written, run `sherpa apply` again (ADR-0030) |
| `symlink in the path — never written through (skipped)` | the file or one of its directories is a symlink; sherpa writes only real files (ADR-0031) — `AGENTS.md → CLAUDE.md` is managed as `CLAUDE.md` |

After the write: the checker summary, files skipped since the preview (`! CLAUDE.md  changed since the preview
(skipped)`), then `N files written · harness_rev <12 hex> → .sherpa/state.json`. On a rollback:
`check: 1 new FAIL — rolled back, nothing written` followed by the findings; on a write error:
`write failed: .claude/docs/modules/two.md: [Errno 28] No space left on device — rolled back, nothing written`.
Should the rollback fail too, the line `rollback failed for: <paths> — restore with \`git checkout -- <path>\`
or \`git clean\`, then \`sherpa adopt\` rebuilds the state` names the way out.

## The state and `harness_rev`

`.sherpa/state.json` records, per file, the ownership mode (`managed`, `blocks`, `json-hooks`), the origin
(`generated`, or `adopted` by [`sherpa adopt`](adopt.md)), the plan entry and the hashes sherpa wrote — one per managed
file, one per block. `harness_rev` is a hash over all of them plus the sherpa version: it changes exactly when
sherpa's share of the harness changes. Facts blocks are stamped `as of <date>` — the scan window end — and
nothing else (ADR-0019): a trunk move without activity in a unit, or a new sherpa version, rewrites no block;
the trunk revision lives here in the state and in the plan header, once each. The outcome hook stamps it on every label, so `sherpa status` can compare
harness versions. `applied_at` is the only timestamp Sherpa ever writes and lives only here. Commit the state
(ADR-0005). Schema: [`harness-state.schema.json`](../../src/sherpa/schemas/harness-state.schema.json). The state
is written atomically and is an index over the files: lost or torn, `sherpa adopt` rebuilds it (ADR-0017).

## The outcome hook

Installed with every apply (ADR-0008): `.claude/hooks/sherpa-outcome.py`, wired in `.claude/settings.json` for
`UserPromptSubmit`, `PostToolUse` (`Bash|Edit|Write|MultiEdit`), `PostToolUseFailure` (`Bash`) and `Stop`.
It is stdlib-only, fail-open and never prints. Per execution it appends one line to
`.sherpa/telemetry/outcomes.ndjson` with a label — `success` (last test run green, or a PR created), `failed`
(last test run red), `unknown` (no signal) — the tool signals, and the `harness_rev`. A follow-up prompt that
starts with a correction ("no, that's wrong", "doesn't work", …) records a `correction` for the previous
execution. **Privacy:** each record also stores the first 160 characters of the prompt, so a label can be read
next to what was asked; everything stays on the machine — `.sherpa/telemetry/` is ignored by git through the
`.gitignore` sherpa writes there, nothing is uploaded, and there is no other free text. Remove the hook entries
from `.claude/settings.json` to store nothing. Details:
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
| Everything is `! exists, not managed by sherpa` | the repo already has a `.claude/` — those files have no state record | `sherpa adopt` takes them over and marks the entries they cover |
| `sherpa apply: .sherpa/state.json is unreadable (…)` | a crash left a torn state, or the file is foreign | `sherpa adopt` rebuilds it from the harness files (ADR-0017) |
| `both .agents/ and .claude/ exist — where should owner docs and skills live?` | two homes, nothing decided, no terminal | set `[apply] home` in `sherpa.toml`, or run `apply` interactively once — the answer is remembered |
| No `CLAUDE.md`, no hook after apply | the repo had `AGENTS.md` and no `.claude/`, so only `agents-md` was detected | add `targets = ["claude", "agents-md"]` to `[apply]` |
| `status` shows `~ block facts updated` right after `apply` | `apply` was run with an older model than the plan | run `sherpa plan` then `sherpa apply` |
| CLAUDE.md got a block at the very end, below my own sections | intended — sherpa appends, never reorders | move the block; its markers are what matters, not its position |
| The hook writes nothing | `settings.json` entries missing (someone removed them) or no `python3`/`python` on the PATH | `sherpa apply` merges the entries back; `sherpa check` C6 verifies the wiring |
| I want sherpa to take a hand-edited block back | delete your changes inside the block, or remove the file's record from `.sherpa/state.json` | the next apply regenerates it |
| Rollback although my files are fine | the write introduced a FAIL — usually a link into a file the plan no longer creates | read the findings; `--no-check` writes anyway |

## See also

[`sherpa plan`](plan.md) · [`sherpa status`](status.md) · [`sherpa check`](check.md) ·
[concepts/harness-apply.md](../concepts/harness-apply.md) · ADR-0008 (dry run, outcome minimum), ADR-0013
(managed blocks, checker, selection).
