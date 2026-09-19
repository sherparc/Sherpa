# `sherpa doctor`

Every prerequisite as one line with a fix — the first command on a new machine and the one to paste into a bug
report. Nothing is written; the only network access is the release check, and it is optional.

## Synopsis

```
sherpa doctor [REPO] [--offline]
```

## Checks

| Check | Level | What passes | Fix shown on a problem |
|---|---|---|---|
| `python` | fail | ≥ 3.12; shows the interpreter path | install Python ≥ 3.12 |
| `git` | fail / hint | `git` on the `PATH`; a hint below 2.20 | install git and open a new shell |
| `install` | ok / hint | how this sherpa was installed: `uv`, `pipx`, `pip` or an editable clone; a hint when the installer is no longer on the `PATH` | reinstall the tool |
| `repository` | fail | `REPO` is inside a git work tree | `cd` into it or `git init` |
| `origin` | fail | a remote named `origin`; shows its URL | `git remote add origin <url>` |
| `sherpa.toml` | ok / fail | absent, or parses with known keys only | the offending key |
| `trunk` | ok / hint / fail | `origin/<trunk>` resolves (ADR-0003); a hint when it was guessed from the candidate list instead of `origin/HEAD` or `sherpa.toml` | `git remote set-head origin -a` or `trunk` in `sherpa.toml` |
| `runtime` | ok / hint | an agent runtime is visible: `claude`, `codex`, `cursor` or `gemini` on the `PATH`, or `.claude/`, `CLAUDE.md`, `.agents/`, `AGENTS.md` in the repo — and the targets `apply` will render for it (`→ targets: …`: `sherpa.toml [apply] targets`, then the state, then the files, ADR-0015); a hint when Claude Code is on the `PATH` but `claude` is not a target, because a root `AGENTS.md` alone selects `agents-md` and no outcome hook would be installed | sherpa writes the harness anyway; install a runtime to use it; `[apply] targets = ["claude", "agents-md"]` in sherpa.toml, or `.claude/` in the repo |
| `layout` | ok / hint | where the core will live — `sherpa.toml [apply] home`, then the state, then the directories; a hint when both `.agents/` and `.claude/` exist and nothing decides (the case `apply --yes` and `adopt` refuse, ADR-0036) | `[apply] home = ".agents"` or `".claude"` in `sherpa.toml` |
| `repositories` | ok / fail | one repository: no directory in the tree with a `.git` of its own — a harness clone under `.claude/`, a submodule, a vendored clone stop `apply` and `adopt` (ADR-0045); names up to five | move the clone out of the tree, or run sherpa in that repository |
| `update` | ok / hint | the latest release (PyPI first, ADR-0053; the GitHub API with a token or `git ls-remote` without one when the index is silent, ADR-0035) is not newer than this sherpa; unreachable or no access is a hint, never a failure | `sherpa self-update`, or `gh auth login` |

Levels: `✓` ok, `!` hint (sherpa works, you should know), `✗` fail (blocks a command: `scan`, or `apply` and `adopt` for a nested repository). Exit 1 only on a fail.

## Options

| Option | Effect |
|---|---|
| `REPO` | repository root (default `.`) |
| `--offline` | skip the `update` check — no network at all |
| `--json` | the checks as JSON: `{"sherpa", "checks": [{"name", "level", "detail", "fix"}], "problems", "hints"}` — the exit code is unchanged |

`SHERPA_NO_UPDATE_CHECK=1` has the same effect as `--offline` and also silences the daily hint of the other
commands ([self-update](self-update.md)).

## Output

```console
$ sherpa doctor
sherpa doctor — 0.5.0
  ✓ python       3.12.3 at /home/dev/.local/share/uv/tools/sherparc/bin/python3
  ✓ git          git version 2.43.0 (/usr/bin/git)
  ✓ install      sherpa 0.5.0 via uv (/home/dev/.local/bin/uv)
  ✓ repository   /home/dev/shop
  ✓ origin       git@github.com:example/shop.git
  ✓ sherpa.toml  absent — defaults apply
  ! trunk        origin/main @ 896aa9bb1f (guessed from candidates)
    hint: `git remote set-head origin -a` or `trunk` in sherpa.toml [scan] makes it explicit
  ✓ runtime      claude (Claude Code CLI), .claude/ or CLAUDE.md in the repo → targets: claude, agents-md
  ✓ update       0.5.0 is current (via PyPI)
0 problems, 1 hints.
```

Outside a repository the run stops after the environment checks:

```console
$ sherpa doctor /tmp --offline
sherpa doctor — 0.5.0
  ✓ python      3.12.3 at /usr/bin/python3
  ✓ git         git version 2.43.0 (/usr/bin/git)
  ✓ install     sherpa 0.5.0 via pip (/usr/bin/python3)
  ✗ repository  /tmp is not a git repository
    fix: cd into the repository or `git init`
1 problems, 0 hints.
```

## Exit codes

| Exit | When |
|---|---|
| 0 | no fail (hints allowed) |
| 1 | at least one fail |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `update` says `no release published yet` | the token works, but the repository has no GitHub release | nothing to do; `git pull` on a clone |
| `update` says `no access without a token: git ls-remote failed …` | no token and no git credentials for GitHub | `gh auth login`, `GITHUB_TOKEN`, or a credential helper / ssh key |
| `trunk` fails although the branch exists | it exists locally only; sherpa reads `origin/<branch>` | `git fetch origin`, then `git remote set-head origin -a` |
| `install` hints that `uv` is not on the `PATH` | sherpa was installed with `uv tool` from a shell that had it | reinstall uv or add `~/.local/bin` to the `PATH` |

## See also

[`sherpa self-update`](self-update.md) · [getting started](../getting-started.md) · [files, exit codes,
environment](../reference/files-and-exit-codes.md) · ADR-0018.
