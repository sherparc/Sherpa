# ADR-0013 — `apply` owns marked blocks, not whole files; the checker has one source and is deployed as a copy

**Status:** accepted · **Date:** 2026-09-17 · **Decision:** Andrei (M3 design questions)

## Context
Owner docs and agents are written by sherpa **and** by humans. Terraform's model — a resource is either managed
or not — was the plan until M3: a file with a hash in the state, any hand edit turns it into `! hand-edited` and
sherpa never touches it again. In a harness that is the wrong granularity: the moment a developer adds one line
to an owner doc, the scanner facts in it (hotspots, dependents, commit counts) stop being updated and drift from
day one — the exact failure mode a harness generator exists to prevent.

Second, the plan said the checker "is installed as well". A copy of the rules in every target repo drifts from
the product's rules and violates the owner principle (one implementation per fact).

## Decision
1. **Three ownership modes**, recorded per file in `.sherpa/state.json`:
   - `managed` — the whole file is sherpa's (hook script, checker copy, telemetry `.gitignore`). Hash in the state;
     a differing hash is a hand edit and the file is skipped with `!`.
   - `blocks` — the file is **seeded once**; afterwards sherpa owns only the text between
     `<!-- sherpa:begin <name> -->` and `<!-- sherpa:end <name> -->` (in YAML front matter: `# sherpa:begin …`).
     One hash per block. A hand-edited block is skipped on its own; the other blocks of the file are still
     regenerated; everything outside the blocks belongs to the humans and is never read for drift.
   - `json-hooks` — `.claude/settings.json`: sherpa's hook entries are merged in by identity (the command names
     `sherpa-outcome.py`); every other key and hook stays.
   A file that exists without a state record is never touched (`! exists, not managed — sherpa adopt`), except
   `CLAUDE.md`, where the block is appended.
2. **`harness_rev`** = hash over everything sherpa owns (managed file hashes and block hashes, sorted) plus the
   sherpa version. It changes exactly when sherpa's share changes, and the outcome hook stamps it on every label.
3. **One checker, deployed as a copy.** `src/sherpa/check.py` is a single stdlib-only file; `apply` writes it
   as the managed file `.claude/scripts/sherpa-check.py` (version stamped). Run standalone it applies the same
   rules; when an installed `sherpa` is importable it delegates to it, so the newer rules always win. It also owns
   the marker grammar and the content hash — drift is measured with the code that checks it.
4. **Rollback only on new FAILs.** `apply` runs the checker before and after writing; it rolls back when the write
   introduced a FAIL. Pre-existing FAILs from hand-written files are reported but do not block (a repo with one
   broken link would otherwise be locked forever).
5. **Selection (Terraform model):** every `propose` unless `decision: reject`, every `skip` with `decision:
   accept`. One question, `apply? [y/N]`; `--yes` for CI; `--dry-run` never asks. Per-entry prompting is left to
   `/sherpa-plan` in Claude Code (M7).

## Reasoning
- Block ownership is the practice of Ansible `blockinfile` and of generated sections in config files: the tool
  keeps its section current, the human keeps the rest. Terraform has no equivalent because its resources are not
  co-authored; harness files are.
- No sherpa version inside the blocks: an upgrade must not rewrite every facts block in a repo. The version lives
  in the state and in `harness_rev`.
- Hashes are computed with line endings normalised, so a CRLF checkout (git autocrlf) is not a hand edit.
- A copy that delegates to the installed product gives both worlds — colleagues and CI without sherpa still get the
  rules — without a second implementation.

## Consequences
- The state schema (`harness-state.schema.json`) has `mode`, `origin`, `hash`, `blocks` per file.
- Generated markdown carries block markers; the plan's earlier `sherpa:generated <version> hash=…` marker is
  superseded (the hash lives in the state, not in the file).
- `sherpa status` reports per block; `sherpa check` C5 fails on broken markers, C8 warns on drift.
- `adopt` (next slice) records foreign files as `origin: adopted` without blocks; they stay hand-edited forever.
