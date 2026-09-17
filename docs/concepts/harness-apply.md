# `sherpa apply`, `status`, `check` — from the approved plan to files, and back

> Owner of: invocation, ownership modes, generated files, state, outcome hook, checker rules. Field semantics of
> the state belong to [`harness-state.schema.json`](../../src/sherpa/schemas/harness-state.schema.json) (v1); code in
> [`src/sherpa/apply/`](../../src/sherpa/apply/) (`render.py` files, `__init__.py` actions and write, `state.py`,
> `status.py`) and [`src/sherpa/check.py`](../../src/sherpa/check.py). Principles: ADR-0008 (dry run, outcome
> minimum), ADR-0013 (managed blocks, single-source checker), ADR-0007/0017 (adopt, rebuildable state).
> Status: M3d, v0.6.0.

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
```

After `--yes`: `check: 0 FAIL, 0 WARN` · `18 files written · harness_rev c38498363846 → .sherpa/state.json`.
The second run lists eighteen `=` and ends with `nothing to do.` — that is the determinism guarantee made visible.

## What each entry becomes (ADR-0015: neutral core + adapters)

`home` (`.agents` by default, `.claude` for Claude-only teams; asked when both exist) holds the runtime-neutral
core; each target in `targets` adds its projection. Sherpa owns the blocks named below; humans own the rest.

| Plan entry | Core `<home>/…` | `claude` | `agents-md` |
|---|---|---|---|
| always | `scripts/sherpa-check.py`, `.sherpa/telemetry/.gitignore` | `CLAUDE.md` block `harness` (six lines; `@AGENTS.md` import in a new file when AGENTS.md exists or is generated) | `AGENTS.md` block `harness`: overview, index of the 20 most active nested files (the rest counted), root-module facts |
| `outcome` | — | `.claude/hooks/sherpa-outcome.py`, hook entries in `.claude/settings.json` | — |
| `owner-doc`, `test-infra` | `docs/modules/<slug>.md` block `facts` | `<unit>/CLAUDE.md` block `harness` (`@AGENTS.md`, or the facts when `agents-md` is off) | `<unit>/AGENTS.md` block `facts` + link to the owner doc |
| `agent` | — | `.claude/agents/<slug>.md` blocks `knowledge` (manifest: `always` = owner doc, `on_demand` = generator skills) and `manifest` | — |
| `librarian` | `skills/<slug>-sync/SKILL.md` block `scope` | stub under `.claude/skills/` when `home` ≠ `.claude` | — |
| `skill` | `skills/regenerate-<family>/SKILL.md` block `facts` | stub under `.claude/skills/` when `home` ≠ `.claude` | — |

Nested files are the market's proximity loading (the closest `AGENTS.md`/`CLAUDE.md` wins) filled with measured
facts and kept current; the owner doc stays the single place for detail. Slugs are lower-case `[a-z0-9-]`; two
units with the same slug get the scope appended (`shop-core--src-shop-core.md`). Every file follows the owner
principle: facts have exactly one owner; agents carry a role and a manifest and say so; generated code is
regenerated, not explained (ADR-0011). Dates in blocks come from the model (`as of`), never from a clock, and
the sherpa version is not in the blocks — an upgrade must not rewrite every doc.

## Ownership: managed, blocks, json-hooks (ADR-0013) — never overwrite, only add (ADR-0016)

In the user's repository Sherpa creates, appends and merges; it rewrites only bytes it wrote itself and that
nobody changed since (hash in the state). Everything else is skipped with a reason. The dry run shows exactly
what a file's line means:

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
| `! exists with sherpa markers but no state record — sherpa adopt` | markers present, no record (a deleted state, a copied file) — somebody's content until adopt says otherwise |
| `! block facts not written by sherpa (skipped)` | a block with one of Sherpa's names that has no hash in the record — not Sherpa's, never touched |

Hashes ignore line endings (`\r\n` = `\n`): a CRLF checkout is not a hand edit.

## State — `.sherpa/state.json`

```json
{
  "schema_version": 1,
  "sherpa": "0.4.0",
  "harness_rev": "c38498363846",
  "home": ".agents",
  "targets": ["claude", "agents-md"],
  "plan": {"trunk": "origin/main", "rev": "5db69c4d…", "as_of": "2026-03-01T00:00:00Z"},
  "applied_at": "2026-09-16T22:07:12Z",
  "files": {
    ".claude/agents/pay.md": {"mode": "blocks", "origin": "generated", "entry": "agent:pay:svc/pay",
                              "blocks": {"knowledge": "…", "manifest": "…"}},
    "svc/pay/AGENTS.md": {"mode": "blocks", "origin": "generated", "entry": "owner-doc:pay:svc/pay",
                          "blocks": {"facts": "…"}},
    ".claude/hooks/sherpa-outcome.py": {"mode": "managed", "origin": "generated", "hash": "9c1e…"}
  }
}
```

`harness_rev` = hash over all managed file and block hashes plus the sherpa version — the number a harness change
has to be measured against. `applied_at` is the only clock in the whole apply; the state is rewritten only when
something changed. Plan and state are checked in (ADR-0005), the model is not.

## Adopt — existing harnesses and a rebuildable state

The harness files are the source of truth; the state is an index over them (ADR-0017). `sherpa adopt` is the
one operation that builds that index from the files instead of from a write: every file under the homes and
every `CLAUDE.md`/`AGENTS.md` is classified by path, compared with the plan's rendering where there is one, and
recorded as sherpa's (`generated`) only where the bytes prove it — a whole file that equals its rendering, a
block that equals its rendering, a base file sherpa names itself. Everything else is `adopted`: yours, never
touched by `apply`, never drift in `status`, no C8. Adopted agents and docs are linked to units (name, then path
mentions) and **cover** the plan entries they fill; `selected()` leaves a covered entry out unless a human
accepts it. The rules, the console marks and the gaps are in [commands/adopt.md](../commands/adopt.md).

Index files (`state.json`, `harness-plan.yaml`) are written atomically (temp file + `os.replace`); a torn or
foreign state fails every reader with the way out in the message, and `adopt` rebuilds it — after an unchanged
`apply`, with the same `harness_rev`.

## Outcome minimum — the hook (ADR-0008)

`apply` installs `.claude/hooks/sherpa-outcome.py` (stdlib, fail-open, never prints) and wires it into
`.claude/settings.json` for `UserPromptSubmit`, `PostToolUse` (`Bash|Edit|Write|MultiEdit`), `PostToolUseFailure`
(`Bash`) and `Stop`. Per execution (one prompt until the next Stop) it appends one line to
`.sherpa/telemetry/outcomes.ndjson`:

```json
{"kind": "outcome", "id": "<session>:3", "harness_rev": "c38498363846", "label": "success",
 "signals": {"bash": 4, "bash_errors": 0, "edits": 2, "tests_run": 1, "tests_failed": 0, "last_test": "green",
             "pushed": false, "pr_created": false}, "prompt": "add a test for …"}
```

| Label | When |
|---|---|
| `success` | the last test run in the execution was green (`pytest`, `dotnet test`, `npm test`, `go test`, `cargo test`, `mvn test`, …), or a pull request was created |
| `failed` | the last test run was red (`PostToolUseFailure`) |
| `unknown` | no signal — a pure question/answer turn; honest, not bad |
| correction | a follow-up prompt that starts with "no, that's wrong", "doesn't work", … adds a `correction` record for the previous execution — the cheapest outcome signal there is |

Telemetry never enters the repo: `.sherpa/telemetry/.gitignore` ignores everything but itself. Privacy note: the
record carries the first 160 characters of the prompt (`"prompt"` above) — the only free text sherpa ever
stores, local only, never uploaded; a team that wants none of it removes the hook entries from
`.claude/settings.json` and loses only the outcome labels. The evaluation
(labels per `harness_rev`, trend, regression between two harness versions) is M5; `sherpa status` already shows
the counts per `harness_rev`.

## Checker rules — `sherpa check` and the deployed copy

| Rule | Level | What |
|---|---|---|
| C1 | FAIL | every `.claude/agents/*.md` has front matter with `name` and `description` (Claude Code needs both) |
| C2 | FAIL | every `SKILL.md` under `.claude/skills/` or `.agents/skills/` has front matter with `name` and `description` |
| C3 | FAIL | every path under `knowledge.always` / `knowledge.on_demand` exists (relative to `.claude/`) |
| C4 | FAIL | relative file links in `.claude/**`, `.agents/**` and every `CLAUDE.md`/`AGENTS.md` resolve (links without an extension are wiki pages, `archive/` is history — both skipped) |
| C5 | FAIL | `sherpa:begin/end` markers are balanced, named and unique per file |
| C6 | FAIL | `.claude/settings.json` is valid JSON; every hook command under `$CLAUDE_PROJECT_DIR` points to an existing file |
| C7 | WARN | agent > 150 lines, owner doc > 600, skill > 250 — a fat agent is a rotation candidate; a nested `CLAUDE.md`/`AGENTS.md` > 8 KiB and a root one > 32 KiB — a proximity file lands whole in the context (Hermes: a tool result on the first touch of the directory, ceiling 32 KiB; ADR-0029) |
| C8 | WARN | with a state: managed files or blocks whose hash differs, or that are missing |

`src/sherpa/check.py` is one stdlib-only file. `apply` deploys it as `<home>/scripts/sherpa-check.py` with the
version stamped in; run standalone (`python3 .agents/scripts/sherpa-check.py`) it applies the same rules, and when
an installed `sherpa` is importable it delegates to that — installed rules are never older than the copy.
`SHERPA_CHECK_STANDALONE=1` forces the copy. `status` notes when the copy is older than the installed sherpa.

`apply` runs the checker before and after writing and rolls back when the write introduced a **new** FAIL;
pre-existing FAILs from hand-written files are reported but never block.

## `sherpa status`

Example (lines exactly as `status` renders them; see `test_status_reports_drift_orphans_outcomes_and_version`):

```console
$ sherpa status .
sherpa status — harness_rev c38498363846, applied 2026-09-16T22:07:12Z
drift: 3 files
  ! .claude/agents/pay.md            block manifest hand-edited (skipped)
  ~ .agents/docs/modules/pay.md      block facts updated
  ? .claude/agents/old.md            in the state, no longer in the plan
check: 0 FAIL, 1 WARN
  WARN C7 .claude/agents/pay.md: 162 lines > budget 150 (agent)
outcomes: 12 executions labelled, 1 corrections
  c38498363846 (current): 7 success, 2 failed, 3 unknown
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
