# Files, exit codes, environment

## Files Sherpa reads

| Path | Read by | Notes |
|---|---|---|
| the git repository, `origin/<trunk>` | `scan` | never the working tree or the checked-out branch |
| `sherpa.toml` | all | optional; [configuration](configuration.md) |
| `.sherpa/codebase-model.json` | `plan`, `apply`, `status` | rescanned by `plan` when missing, stale or of an old schema |
| `.sherpa/harness-plan.yaml` | `plan` (decisions), `apply`, `status` | the previous plan's `decision:` values are carried over |
| `.sherpa/state.json` | `apply`, `status`, `check` (C8), the outcome hook (`harness_rev`) | empty state when missing |
| `.claude/**`, `CLAUDE.md` | `apply` (current content), `check`, `status` | |
| `.sherpa/telemetry/outcomes.ndjson` | `status` | written by the outcome hook |

## Files Sherpa writes

| Path | Written by | Commit it? |
|---|---|---|
| `.sherpa/codebase-model.json` | `scan`, `plan` | **no** — regenerated from the trunk; add to `.gitignore` |
| `.sherpa/harness-plan.yaml` | `plan` | **yes** — it carries the team's decisions (ADR-0005) |
| `.sherpa/state.json` | `apply` | **yes** — what sherpa owns and the harness version (ADR-0005) |
| `.claude/docs/modules/*.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md` | `apply` | yes — the harness |
| `.claude/hooks/sherpa-outcome.py`, `.claude/scripts/sherpa-check.py`, `.claude/settings.json` (hook entries) | `apply` | yes |
| `CLAUDE.md` (block `harness`) | `apply` | yes |
| `.sherpa/telemetry/.gitignore` | `apply` | yes (it ignores everything else in the directory) |
| `.sherpa/telemetry/outcomes.ndjson`, `session-*.json` | the outcome hook | **no** — ignored via the file above |

All files are UTF-8 with `\n` line endings; paths inside them use `/` on every platform. Hashes in the state are
computed with line endings normalised, so an autocrlf checkout is not a hand edit.

Suggested `.gitignore` in a target repository:

```gitignore
.sherpa/codebase-model.json
```

## Exit codes

| Code | Meaning | Commands |
|---|---|---|
| 0 | success — including a dry run, an aborted question and "nothing to do" | all |
| 1 | error: git (no repository, no origin, no trunk), configuration, plan or state file invalid or missing, stale plan, rollback after a new checker FAIL, checker FAIL | all |
| 2 | command not implemented yet (`adopt`) | `adopt` |

Errors go to stderr as `sherpa <command>: <message>`; the message names the fix where there is one
(`— run `sherpa plan` first`, `Fix: 'git remote set-head origin -a' or 'trunk' in sherpa.toml`).

## Environment

| Variable | Used by | Effect |
|---|---|---|
| `CLAUDE_PROJECT_DIR` | the outcome hook, the deployed checker | repository root when run by Claude Code; the checker falls back to `.` |
| `SHERPA_CHECK_STANDALONE=1` | the deployed checker | run the copy's own rules instead of delegating to an installed sherpa |
| `SHERPA_UPDATE_GOLDENS=1` | the test suite | rewrite `tests/goldens/` after an intended rule change |

Sherpa needs `git` on the `PATH` and Python ≥ 3.12. The outcome hook and the deployed checker need only a
Python interpreter (`python3`, or `python` on Windows) — no sherpa installation, no third-party packages.

## Stdout and stderr

| Command | stdout | stderr |
|---|---|---|
| `scan` | the model with `--out -`, else nothing | summary line, errors |
| `plan` | console view; the YAML with `--out -` | with `--out -` the console view; scan/rescan notices; errors |
| `apply` | file list, question, result | errors |
| `status`, `check` | the report | errors |

Console output uses `✓`/`✗` and `→`; on consoles that cannot encode them (Windows code pages, some CI logs) the
characters are replaced instead of crashing the command.
