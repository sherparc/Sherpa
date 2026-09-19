# `sherpa self-update`

Install the latest release with the installer that owns this copy — `uv tool`, `pipx` or `pip`. The index is
PyPI (ADR-0053), the GitHub release the fallback (ADR-0018). A clone (editable install) is refused with the fix:
`git pull`.

## Synopsis

```
sherpa self-update [--check]
```

## How it works

1. **Find the release.** First PyPI, without a token: `GET https://pypi.org/pypi/sherparc/json`, the
   version under `info.version`. When the index has no project yet or cannot be reached, the GitHub release:
   with a token from `GITHUB_TOKEN`, `GH_TOKEN` or `gh auth token` `GET /repos/sherparc/Sherpa/releases/latest`;
   without a token: `git ls-remote --tags` over the user's git credentials — the https URL first (credential
   helper), then ssh — and the highest `v*` tag wins (ADR-0035); git never prompts (`GIT_TERMINAL_PROMPT=0`).
   The tag `v<version>` is compared numerically with the running version; a pre-release suffix sorts below the
   plain version.
2. **Fetch.** From PyPI the installer fetches the wheel itself — the source is the pinned requirement
   `sherparc==0.8.1`, no download by sherpa. From a GitHub release with a token the wheel attached by
   `release.yml` is downloaded through the API into a temporary
   directory under its own file name (`sherparc-0.8.1-py3-none-any.whl` — pip reads the version and the
   tags from the name, PEP 427). Without a token, or when no wheel is attached, the source is the tag's git URL
   (`git+https://github.com/sherparc/Sherpa.git@v0.7.3`) through the user's git credentials.
3. **Install.** The command of the detected installer:

   | Installer | Detected by | Command |
   |---|---|---|
   | `uv` | `sys.prefix` under `uv/tools/` | `uv tool install --force --reinstall <source>` |
   | `pipx` | `sys.prefix` under `pipx/venvs/` | `pipx install --force <source>` |
   | `pip` | any other environment | `<python> -m pip install --upgrade <source>` |
   | editable | `src/sherpa/` next to a `pyproject.toml` | refused — `git pull` |

Nothing in the target repositories changes; the next `sherpa apply` refreshes the deployed checker and hook
(their version stamp is what `sherpa status` compares).

## Options

| Option | Effect |
|---|---|
| `--check` | only report whether a newer release exists (exit 0 either way) |

## The daily hint

Every everyday command (`scan`, `plan`, `apply`, `adopt`, `status`) checks for a newer release **at most once
per 24 hours, in the background**: a daemon thread queries the API and writes the result to
`update-check.json` in the cache directory; the command itself prints only what an earlier check cached, so the
hint costs no waiting and can never fail a command. The line appears on stderr, after the command's own output,
only on a terminal:

```
sherpa 0.6.0 is available (you have 0.5.0) — `sherpa self-update`; SHERPA_NO_UPDATE_CHECK=1 hides this.
```

| Switch | Effect |
|---|---|
| `SHERPA_NO_UPDATE_CHECK=1` | no check, no hint (also `doctor --offline`) |
| `CI` set, stderr not a terminal | no hint — CI logs, hooks and pipes stay clean |
| `doctor`, `self-update`, `check` | never hint (`check` runs inside hooks) |
| `SHERPA_CACHE_DIR` | cache location; default `$XDG_CACHE_HOME/sherpa` or `~/.cache/sherpa`, `%LOCALAPPDATA%\sherpa` on Windows |

## Output

```console
$ sherpa self-update
sherpa 0.8.1 is available (you have 0.7.9): https://pypi.org/project/sherparc/0.8.1/
→ uv tool install --force --reinstall sherparc==0.8.1
sherpa 0.8.1 installed via uv.

$ sherpa self-update --check
sherpa 0.8.1 is current (latest release: v0.8.1).

$ sherpa self-update            # the index silent, a token present: the GitHub release
sherpa 0.8.1 is available (you have 0.7.9): https://github.com/sherparc/Sherpa/releases/tag/v0.8.1
→ uv tool install --force --reinstall /tmp/sherpa-update-k3j/sherparc-0.8.1-py3-none-any.whl
sherpa 0.8.1 installed via uv.
```

## Exit codes

| Exit | When |
|---|---|
| 0 | installed, or already current, or `--check` |
| 1 | no release reachable (network, token), an editable clone, or the installer failed — the message names the reason |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `no access without a token: git ls-remote failed for …` | no token and no git credentials for the repository (both URLs are named with git's last line) | `gh auth login`, `GITHUB_TOKEN=…`, or a credential helper / ssh key for GitHub |
| `GitHub API 401/403 … the token has no access` | the token is expired or scoped without repository read | renew it, or unset it to use git credentials |
| `no release published yet` / `no release tag on …` | PyPI has no project and GitHub nothing released | wait, or install from the repository (`git+https://…`) |
| `… is not a valid wheel file name (PEP 427)` | the release asset has an unexpected name | check the release's assets; `release.yml` attaches the wheel under its build name |
| `this sherpa runs from a clone` | editable install | `git pull` in the clone |
| `uv failed: …` | the installer's own error (network, permissions) | run the printed command by hand |
| the hint keeps showing after an update | the cache is refreshed once a day | harmless; `rm ~/.cache/sherpa/update-check.json` forces a new check |

## See also

[`sherpa doctor`](doctor.md) · [files, exit codes, environment](../reference/files-and-exit-codes.md) ·
ADR-0018.
