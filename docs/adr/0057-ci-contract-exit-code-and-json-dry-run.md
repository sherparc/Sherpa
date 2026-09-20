# ADR-0057 — The CI contract: `status --exit-code` and `apply --json`

**Status:** accepted · **Date:** 2026-09-20 · **Deciders:** Andrei · **Relates to:** ADR-0008 (dry run first),
ADR-0013 (state and drift), ADR-0024 (the plugin calls the CLI), ADR-0034 (a torn state is reported, never fatal)

## Context

`status` exited 1 on a checker FAIL and 0 on everything else — drift, a stale plan, a torn state were lines to
read. A pipeline that wants "is the harness what `apply` would write?" had to parse `--json` with a JSON tool
(plan §11 F31, Q29, carried through four reviews). The dry run of `apply` was prose only while `status`,
`check` and `doctor` had `--json` (§14 F63); the plugin commands of M7a (`/sherpa-apply` "shows the dry run,
then `--yes`") and every CI gate would have scraped `render_actions`, and the end-to-end theses did exactly
that — the e2e drift of §13 F54 came from wording changes in lines a test had matched.

Terraform's answer is `plan -detailed-exitcode` (0 no changes, 1 error, 2 changes) and `plan -json` /
`show -json`; `git diff --exit-code` makes the difference an exit code only when asked.

## Decision

1. **`sherpa status --exit-code`** exits **2** when the harness is not current, **1** on a checker FAIL as
   before (a FAIL wins), **0** otherwise. "Current" means: `apply` would write nothing — no `+ ~ - ?` drift
   line (a file to add, change, recreate or remove, an orphan record) — the plan was made from the trunk's
   rev, and the state is readable. A hand-edited block (`!`) is the team's and never makes the harness not
   current: `apply` skips it and says `nothing to do.`. Without the flag nothing changes; `status --json`
   carries the verdict as `"current"`.
2. **`sherpa apply --json`** prints the dry run as one object and implies `--dry-run`: `sherpa`, `dry_run`,
   `home`, `targets`, `notes` (what the console prints as `note:`), `plan` (trunk, rev, entries, selected),
   `actions` (one per file: `op` as the list's symbol, `path`, `entry` or `null` for a base file, `mode`,
   `detail`) and `counts` (add, change, unchanged, skipped, remove). It comes from the same `Action` list as
   the console, so the two agree line for line; nothing is written, nobody is asked.
3. Exit code 2 is shared with argparse's usage error. They never look alike — a usage error prints the usage
   on stderr and no report, `status` prints the report on stdout — and Terraform's `2` is the contract CI
   authors know; a third code would be sherpa's own.

## Reasoning

- The milestone-step ritual's gate "status clean" is now one command with one exit code instead of a JSON
  tool and a jq expression; the plugin gets a parsable dry run without a second rendering.
- Hand edits stay outside the gate on purpose: ADR-0016's promise is that a team may write into the files,
  and a gate that turns red on a legitimate edit is a gate a team disables.
- The theses can assert the JSON instead of console wording where the claim is about the actions, which is
  where most e2e drift came from.

## Consequences

- `cli.py`: `EXIT_NOT_CURRENT = 2`; `Report.current` in `status.py`; `render_actions_json` in `apply`.
- Docs: `docs/commands/status.md` (options, exit codes, CI use), `docs/commands/apply.md` (`--json` with the
  shape), `docs/reference/files-and-exit-codes.md`, the concept doc's command block.
- Theses E13 (`apply --json` lists what the console listed, writes nothing) and E14 (`--exit-code` 0 / 2 / 0
  around a removed managed file); `test_status_exit_code_says_whether_the_harness_is_current`,
  `test_apply_json_is_the_dry_run_for_scripts`.
- M7a's `/sherpa-apply` reads `apply --json`; the `CI` example in the README uses `status --exit-code`.
