# `sherpa apply`, `status`, `check` — from the approved plan to files, and back

> Owner of: invocation, ownership modes, generated files, state, outcome hook, checker rules. Field semantics of
> the state belong to [`harness-state.schema.json`](../../src/sherpa/schemas/harness-state.schema.json) (v1); code in
> [`src/sherpa/apply/`](../../src/sherpa/apply/) (`render.py` files, `__init__.py` actions and write, `state.py`,
> `status.py`) and [`src/sherpa/check.py`](../../src/sherpa/check.py). Principles: ADR-0008 (dry run, outcome
> minimum), ADR-0013 (managed blocks, single-source checker). Status: M3a, v0.4.0 — `adopt` follows.

Command reference (options, exit codes, troubleshooting): [`sherpa apply`](../commands/apply.md).

## Invocation

```bash
sherpa apply <repo>              # dry run: every file with + ~ = !, then "apply? [y/N]" (no terminal: list only)
sherpa apply <repo> --yes        # write without asking (CI)
sherpa apply <repo> --dry-run    # list only, never asks
sherpa apply <repo> --no-check   # skip the checker after writing (no rollback)
sherpa status <repo>             # drift, checker findings, outcome labels per harness_rev; exit 1 on a FAIL
sherpa check <repo> [--json]     # the structural rules only; the same file runs as .claude/scripts/sherpa-check.py
```

`apply` reads `.sherpa/harness-plan.yaml` and `.sherpa/codebase-model.json` and refuses a stale plan — when
`origin/<trunk>` has moved since the plan was made, `sherpa plan` first (like a saved Terraform plan). It selects
every `propose` entry that is not `decision: reject` and every `skip` entry with `decision: accept`; a rejected
`outcome` entry is an error — a harness without a signal is not created (ADR-0008).

Real output on the five-module test repo (`active_repo` in `tests/test_plan.py`, golden
[`active-apply-console.txt`](../../tests/goldens/active-apply-console.txt)):

```console
$ sherpa apply . --dry-run
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
```

After `--yes`: `check: 0 FAIL, 0 WARN` · `11 files written · harness_rev 5be9c857fd4b → .sherpa/state.json`.
The second run lists eleven `=` and ends with `nothing to do.` — that is the determinism guarantee made visible.

## What each entry becomes

| Plan entry | File | Sherpa owns (blocks) | Humans own |
|---|---|---|---|
| `outcome` (+ always) | `.claude/hooks/sherpa-outcome.py`, hook entries in `.claude/settings.json`, `.sherpa/telemetry/.gitignore` | whole file / the hook entries | everything else in `settings.json` |
| always | `.claude/scripts/sherpa-check.py` | whole file | — |
| always | `CLAUDE.md` | block `harness` (six lines: where facts, agents, skills live; how to check) | the rest; an existing file gets the block appended; a new file in a repo with `AGENTS.md` starts with `@AGENTS.md` so the cross-tool file stays the source |
| `owner-doc`, `test-infra` | `.claude/docs/modules/<slug>.md` | block `facts`: path, kind, files/LOC, commits, authors, deps, dependents, tested by, hotspots, generators → skill | `structure`, `rules`, `key services`, `references` |
| `agent` | `.claude/agents/<slug>.md` | block `knowledge` (front matter manifest: `always` = owner doc, `on_demand` = generator skills), block `manifest` | `name`, `description` (the router catalogue), how to work, handoff contract |
| `librarian` | `.claude/skills/<slug>-sync/SKILL.md` | block `scope`: pathspec, commits/30d, cadence, owner doc | procedure, done-when |
| `skill` | `.claude/skills/regenerate-<family>/SKILL.md` | block `facts`: family, home, generated files, sources, configs, command | procedure, don'ts |

Slugs are lower-case `[a-z0-9-]`; two units with the same slug get the scope appended
(`shop-core--src-shop-core.md`). Every file follows the owner principle from harness practice: facts have exactly
one owner (the owner doc); agents carry a role and a manifest and say so in their first paragraph; generated code
is regenerated, not explained (ADR-0011). Dates in blocks come from the model (`as of`), never from a clock, and
the sherpa version is not in the blocks — an upgrade must not rewrite every doc.

## Ownership: managed, blocks, json-hooks (ADR-0013)

The dry run shows exactly what a file's line means:

| Line | Meaning |
|---|---|
| `+ new` | file does not exist; written from the seed |
| `~ block facts updated` | file exists, sherpa's block differs from the render — only that block is rewritten |
| `~ block facts updated; block manifest hand-edited` | one block regenerated, the other left alone |
| `~ block harness appended` | `CLAUDE.md` existed without markers — the block is appended, nothing else moves |
| `~ hooks added: Stop, …` | `settings.json` existed — sherpa's entries merged in, everything else kept |
| `= unchanged` | nothing to do (the second run is all `=`) |
| `! hand-edited (skipped)` | managed file whose hash differs from the state |
| `! block facts hand-edited (skipped)` | the block's hash differs — the human took it over; the drift stays visible in `status` |
| `! block facts removed by hand (skipped)` | markers deleted; sherpa does not re-insert them |
| `! markers broken: … (skipped)` | begin without end, duplicate names — fix by hand, `sherpa check` C5 says where |
| `! exists, not managed by sherpa — sherpa adopt takes it over` | a file with that path but no state record and no markers |

Hashes ignore line endings (`\r\n` = `\n`): a CRLF checkout is not a hand edit.

## State — `.sherpa/state.json`

```json
{
  "schema_version": 1,
  "sherpa": "0.4.0",
  "harness_rev": "5be9c857fd4b",
  "plan": {"trunk": "origin/main", "rev": "5db69c4d…", "as_of": "2026-03-01T00:00:00Z"},
  "applied_at": "2026-09-16T22:07:12Z",
  "files": {
    ".claude/agents/pay.md": {"mode": "blocks", "origin": "generated", "entry": "agent:pay:svc/pay",
                              "blocks": {"knowledge": "372bee88d9df5d39", "manifest": "a69a440b2d11169f"}},
    ".claude/hooks/sherpa-outcome.py": {"mode": "managed", "origin": "generated", "hash": "9c1e…"}
  }
}
```

`harness_rev` = hash over all managed file and block hashes plus the sherpa version — the number a harness change
has to be measured against. `applied_at` is the only clock in the whole apply; the state is rewritten only when
something changed. Plan and state are checked in (ADR-0005), the model is not.

## Outcome minimum — the hook (ADR-0008)

`apply` installs `.claude/hooks/sherpa-outcome.py` (stdlib, fail-open, never prints) and wires it into
`.claude/settings.json` for `UserPromptSubmit`, `PostToolUse` (`Bash|Edit|Write|MultiEdit`), `PostToolUseFailure`
(`Bash`) and `Stop`. Per execution (one prompt until the next Stop) it appends one line to
`.sherpa/telemetry/outcomes.ndjson`:

```json
{"kind": "outcome", "id": "<session>:3", "harness_rev": "5be9c857fd4b", "label": "success",
 "signals": {"bash": 4, "bash_errors": 0, "edits": 2, "tests_run": 1, "tests_failed": 0, "last_test": "green",
             "pushed": false, "pr_created": false}, "prompt": "add a test for …"}
```

| Label | When |
|---|---|
| `success` | the last test run in the execution was green (`pytest`, `dotnet test`, `npm test`, `go test`, `cargo test`, `mvn test`, …), or a pull request was created |
| `failed` | the last test run was red (`PostToolUseFailure`) |
| `unknown` | no signal — a pure question/answer turn; honest, not bad |
| correction | a follow-up prompt that starts with "no, that's wrong", "doesn't work", … adds a `correction` record for the previous execution — the cheapest outcome signal there is |

Telemetry never enters the repo: `.sherpa/telemetry/.gitignore` ignores everything but itself. The evaluation
(labels per `harness_rev`, trend, regression between two harness versions) is M5; `sherpa status` already shows
the counts per `harness_rev`.

## Checker rules — `sherpa check` and the deployed copy

| Rule | Level | What |
|---|---|---|
| C1 | FAIL | every `.claude/agents/*.md` has front matter with `name` and `description` (Claude Code needs both) |
| C2 | FAIL | every `.claude/skills/*/SKILL.md` has front matter with `name` and `description` |
| C3 | FAIL | every path under `knowledge.always` / `knowledge.on_demand` exists (relative to `.claude/`) |
| C4 | FAIL | relative file links in `.claude/**/*.md` and `CLAUDE.md` resolve (links without an extension are wiki pages, `archive/` is history — both skipped) |
| C5 | FAIL | `sherpa:begin/end` markers are balanced, named and unique per file |
| C6 | FAIL | `.claude/settings.json` is valid JSON; every hook command under `$CLAUDE_PROJECT_DIR` points to an existing file |
| C7 | WARN | agent > 150 lines, owner doc > 600, skill > 250 — a fat agent is a rotation candidate |
| C8 | WARN | with a state: managed files or blocks whose hash differs, or that are missing |

`src/sherpa/check.py` is one stdlib-only file. `apply` deploys it as `.claude/scripts/sherpa-check.py` with the
version stamped in; run standalone (`python3 .claude/scripts/sherpa-check.py`) it applies the same rules, and when
an installed `sherpa` is importable it delegates to that — installed rules are never older than the copy.
`SHERPA_CHECK_STANDALONE=1` forces the copy. `status` notes when the copy is older than the installed sherpa.

`apply` runs the checker before and after writing and rolls back when the write introduced a **new** FAIL;
pre-existing FAILs from hand-written files are reported but never block.

## `sherpa status`

Example (lines exactly as `status` renders them; see `test_status_reports_drift_orphans_outcomes_and_version`):

```console
$ sherpa status .
sherpa status — harness_rev 5be9c857fd4b, applied 2026-09-16T22:07:12Z
drift: 3 files
  ! .claude/agents/pay.md            block manifest hand-edited (skipped)
  ~ .claude/docs/modules/pay.md      block facts updated
  ? .claude/agents/old.md            in the state, no longer in the plan
check: 0 FAIL, 1 WARN
  WARN C7 .claude/agents/pay.md: 162 lines > budget 150 (agent)
outcomes: 12 executions labelled, 1 corrections
  5be9c857fd4b (current): 7 success, 2 failed, 3 unknown
```

Drift is what `apply` would do now (`+ ~ !`), plus `-` files in the state that vanished (apply recreates them)
and `?` orphans — in the state but no longer in the plan (an entry was rejected later). Sherpa never deletes;
orphans are listed until a human removes them. Exit code 1 only on a checker FAIL.

## Determinism and tests

`(plan, model, files, state) → actions` is a pure function (`plan_files`); `write` is the only side effect.
Tested (`tests/test_apply.py`, `tests/test_check.py`): every ownership mode and dry-run line, block merging with
human text around it, hook merging into a foreign `settings.json`, the second run as all `=` with an unchanged
state and tree hash, rollback on a new FAIL, a rescan updating only the facts block, `status` lines, the hook as a
subprocess with the events Claude Code sends, the deployed checker standalone and delegating. Goldens in
`tests/goldens/active-*` (`SHERPA_UPDATE_GOLDENS=1` refreshes them).

Runtime: 61 files for a 15k-file monorepo plan in 0.15 s; the checker on a mature harness in 0.17 s.
