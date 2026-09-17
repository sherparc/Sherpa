# ADR-0036 — A preview never refuses: with two homes and nothing decided, dry runs and `status` assume `.agents` and say so

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei · **Amends:** ADR-0015 (the "refuses without a terminal" clause, for read-only runs only)

## Context

ADR-0015 resolves the home as `sherpa.toml` → state → repository, and when both `.agents/` and `.claude/` exist
with nothing decided it asks on a terminal and refuses otherwise. `apply --dry-run`, `adopt --dry-run` and
`status` pass `ask=False`, so on such a repository they stopped with `both .agents/ and .claude/ exist — where
should owner docs and skills live? Set [apply] home …` — before showing a single file. Measured on a large
repository with a hand-written `.agents/` (skills, rules) and a `.claude/` (a clone of a separate harness
repository): the first `apply --dry-run` produced nothing but that line. A preview that fails on
configuration is not a preview; Terraform's `plan` runs with defaults for every variable it can default and
prints what it assumed.

## Decision

1. `_resolve_layout` takes `preview`. With both homes present, nothing decided and `preview=True`, the home is
   `.agents` (the cross-tool default, as for a bare repository) and a note follows the `targets: … · home: …`
   line: *both .agents/ and .claude/ exist and nothing decides where the core lives — this preview assumes
   .agents; the real run asks, or set [apply] home in sherpa.toml.* `apply --dry-run`, `adopt --dry-run` and
   `status` are previews.
2. A write never guesses: `apply --yes` and `adopt` without a terminal refuse exactly as before; on a terminal
   they ask. `home` and `targets` still have no flags — a layout is a decision, not a per-run option (ADR-0015).
3. The checker copy (`<home>/scripts/sherpa-check.py`, ADR-0017) and the state keep deciding before any
   assumption; the note appears only when nothing decides.

## Reasoning

- The dry run is the product's first contact after `plan`; it must always answer. The default it assumes is
  the same one an interactive Enter would choose, so the preview and the later write agree.
- Refusing the write stays right: the difference between the two homes is where every fact lives (ADR-0015),
  and a wrong guess written to disk costs a `git checkout` plus a re-apply.
- A flag would have been the smaller change but a second precedence source next to the file and the state;
  the note names the two ways that exist.

## Consequences

- `_resolve_layout(repo, state, *, ask, preview=False) -> (home, targets, notes)`; `cli.ASSUMED_HOME`.
- Tests: `test_resolve_layout_preview_assumes_agents_when_both_homes_exist`,
  `test_cli_dry_run_assumes_a_home_and_the_write_refuses_without_a_terminal`.
- `docs/commands/apply.md`, `adopt.md`, `status.md` and `docs/reference/configuration.md` name the assumption.
