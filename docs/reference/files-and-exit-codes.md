# Files, exit codes, environment

## Files Sherpa reads

| Path | Read by | Notes |
|---|---|---|
| the git repository, `origin/<trunk>` | `scan` | never the working tree or the checked-out branch |
| `sherpa.toml` | all | optional; [configuration](configuration.md) |
| `.sherpa/codebase-model.json` | `plan`, `apply`, `status` | rescanned by `plan` when missing, stale or of an old schema |
| `.sherpa/harness-plan.yaml` | `plan` (decisions), `apply`, `status` | the previous plan's `decision:` values are carried over |
| `.sherpa/state.json` | `apply`, `status`, `adopt`, `check` (C8), the outcome hook (`harness_rev`) | empty state when missing; a torn one is an error that names `sherpa adopt` as the fix |
| `.claude/**`, `.agents/**`, every `CLAUDE.md` and `AGENTS.md` | `apply` (current content), `check`, `status` | nested proximity files included |
| `.sherpa/telemetry/outcomes.ndjson` | `status` | written by the outcome hook |

## Files Sherpa writes

| Path | Written by | Commit it? |
|---|---|---|
| `.sherpa/codebase-model.json` | `scan`, `plan` | **no** — regenerated from the trunk; add to `.gitignore` |
| `.sherpa/harness-plan.yaml` | `plan`, `adopt` (`covered:` marks) | **yes** — it carries the team's decisions (ADR-0005) |
| `.sherpa/state.json` | `apply`, `adopt` | **yes** — what sherpa owns and the harness version (ADR-0005); written atomically, rebuildable by `adopt` (ADR-0017) |
| `<home>/docs/modules/*.md`, `<home>/skills/*/SKILL.md`, `<home>/scripts/sherpa-check.py` (`home` = `.agents` or `.claude`) | `apply` | yes — the neutral core |
| `.claude/agents/*.md`, `.claude/hooks/sherpa-outcome.py`, `.claude/settings.json` (hook entries), `.claude/skills/*/SKILL.md` stubs | `apply`, target `claude` | yes |
| `CLAUDE.md`, `<unit>/CLAUDE.md` (block `harness`) | `apply`, target `claude` | yes |
| `AGENTS.md` (block `harness`), `<unit>/AGENTS.md` (block `facts`) | `apply`, target `agents-md` | yes |
| `.sherpa/telemetry/.gitignore` | `apply` | yes (it ignores everything else in the directory) |
| `.sherpa/telemetry/outcomes.ndjson`, `session-*.json` | the outcome hook | **no** — ignored via the file above |
| `<cache>/update-check.json` (`~/.cache/sherpa`, `%LOCALAPPDATA%\sherpa`) | the daily update check | outside the repository; `SHERPA_CACHE_DIR` moves it |

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
| 1 | error: git (no repository, no origin, no trunk), configuration, plan or state file invalid or missing, stale plan, rollback after a new checker FAIL, checker FAIL, a `doctor` fail, `self-update` without a reachable release or with a failed installer | all |
| 2 | usage error — an unknown flag or a missing argument; argparse prints the usage and the message on stderr | all |

Errors go to stderr as `sherpa <command>: <message>`, a rollback included (`sherpa apply: write failed … — rolled back, nothing written`, the details stay on stdout); the message names the fix where there is one
(`— run `sherpa plan` first`, `Fix: 'git remote set-head origin -a' or 'trunk' in sherpa.toml`).

## Environment

| Variable | Used by | Effect |
|---|---|---|
| `CLAUDE_PROJECT_DIR` | the outcome hook, the deployed checker | repository root when run by Claude Code; the checker falls back to `.` |
| `SHERPA_CHECK_STANDALONE=1` | the deployed checker | run the copy's own rules instead of delegating to an installed sherpa |
| `SHERPA_UPDATE_GOLDENS=1` | the test suite | rewrite `tests/goldens/` after an intended rule change |
| `SHERPA_E2E_REPO` | the test suite (`pytest tests/e2e`) | run the end-to-end theses on this local repository instead of the built-in corpus (ADR-0055); it must be clean and is left clean |
| `SHERPA_NO_UPDATE_CHECK=1` | every command | no release check, no daily hint (`doctor --offline` for one run) |
| `SHERPA_CACHE_DIR` | the update check | cache directory instead of `$XDG_CACHE_HOME/sherpa`, `~/.cache/sherpa` or `%LOCALAPPDATA%\sherpa` |
| `GITHUB_TOKEN`, `GH_TOKEN` | `self-update`, `doctor`, the update check | the GitHub fallback of the release check (PyPI needs none): the Releases API with the token, `gh auth token` when unset, `git ls-remote` without one |
| `CI` | every command | no daily hint |

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
