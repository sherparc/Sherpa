# ADR-0035 — `self-update` finds the newest tag with `git ls-remote` when there is no token, and keeps the wheel's own file name

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei · **Amends:** ADR-0018 §2 (the git URL fallback)

## Context

ADR-0018 promised two paths: with a token the wheel from the Releases API, without one the tag's git URL over the
user's git credentials. Neither worked on v0.7.1, as an external review found and a real run confirmed:

1. `download()` named the file after the last segment of the asset's API URL (`…/releases/assets/570259520`),
   which is a number, and fell back to `sherpa_harness.whl`. pip reads the version and the tags from the file
   name (PEP 427) and refuses: `sherpa_harness.whl is not a valid wheel filename`. Every token update with a
   wheel failed at the install step. The tests mocked the installer and never saw pip's answer.
2. The repository is private, so without a token `releases/latest` answers 404 — and `latest_release` raised
   before `self_update` could reach the git fallback. The comment on the fallback described a path that did not
   exist; `doctor` and the daily hint failed the same way.

## Decision

1. `Release` carries the asset's `wheel_name`; `download` saves the bytes under that name (derived from the
   version when the API gives none) and refuses a name that does not match the PEP 427 pattern before pip does.
2. Without a token no API call is made: `latest_tag()` runs `git ls-remote --tags --refs` against the https URL
   (credential helper) and then the ssh URL, with `GIT_TERMINAL_PROMPT=0` so it never prompts, and takes the
   highest `v*` tag by `parse_version` (pre-releases sort below). The install source is `git+<url>@<tag>` as
   before. Both URLs failing names both errors and the three ways in: `gh auth login`, `GITHUB_TOKEN`, git
   credentials.
3. The acceptance bar for the update path is pip itself, not a mocked installer: the wheel's name is checked
   against the PEP 427 pattern in the unit tests, and every release of the update code is smoke-tested with
   `pip install --dry-run` on a wheel the code downloaded.

## Reasoning

- The user's git credentials are the one thing every developer of a private repository has; `git ls-remote`
  is how Renovate and `pip install git+…` discover tags without an API. It also works with no `gh` installed.
- A wheel file name is an interface, not a label; deriving it from the URL was a guess that the tests never
  challenged. Validating before the install turns a cryptic installer error into one line with the cause.
- The API stays the first choice with a token: it gives the wheel (fast, no build) and the release page.

## Consequences

- `update.latest_release(tok)` → `latest_tag()` when `tok` is None; `update._run_git` is the seam the tests
  replace; `update.WHEEL_NAME`; `download(rel, …)` takes the `Release`.
- Tests: `test_latest_release_without_token_uses_git_ls_remote`,
  `test_latest_tag_tries_ssh_after_https_and_names_both_failures`,
  `test_download_writes_wheel_under_its_pep427_name`, `test_wheel_name_pattern_is_pep427`.
- The tokenless path installs from source (`git+…@tag`): slower than the wheel, and it needs `git` on the
  machine — the message says so when it is missing. The public release (ADR-0010) makes the token optional
  for the wheel path too.
