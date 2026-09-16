# ADR-0015 — One runtime-neutral core, one adapter per target; AGENTS.md as a first-class projection

**Status:** accepted · **Date:** 2026-09-17 · **Decision:** Andrei (options A/B; questions on home, nesting, order)

## Context
Until M3a `apply` wrote a Claude Code harness only: owner docs and skills under `.claude/`, subagents, hooks,
`CLAUDE.md`. Many repositories use the cross-tool convention instead or as well: `AGENTS.md` at the root and in
subdirectories, read by Codex, Cursor, Gemini CLI, Copilot, Jules, Amp and others — **the closest file wins**,
so a runtime working in `svc/pay/` loads `svc/pay/AGENTS.md` without any manifest. Skills follow the Agent
Skills standard (`SKILL.md`), which Codex discovers under `.agents/skills/` from the working directory up to the
repository root. Everywhere these files are hand-written; nobody derives them from measurement or keeps them
current. Sherpa's direction (§0 of the plan: an agent runtime of its own, pluggable models) also asks for a core
that does not belong to one runtime.

## Decision
1. **Neutral core under `home`**: owner docs `<home>/docs/modules/`, skills `<home>/skills/<name>/SKILL.md`,
   the checker copy `<home>/scripts/sherpa-check.py`. `home` is `.agents` (default, cross-tool) or `.claude`.
   Resolution: `sherpa.toml [apply] home` beats the state beats the repository — exactly one of `.agents/` and
   `.claude/` present → that one, no question; **both present → the CLI asks** on a terminal and refuses
   without one; **neither present → the user decides, `.agents` is the default** (Enter, `--yes`, `--dry-run`
   or no terminal take it). The answer is remembered in the state.
2. **Targets**: `[apply] targets` ⊆ {`claude`, `agents-md`}; default by detection (`.claude/` or `CLAUDE.md` →
   `claude`; `AGENTS.md` or `.agents/` → `agents-md`; nothing → both), remembered in the state.
   - `claude`: subagents, the outcome hook and `settings.json` entries, root `CLAUDE.md` (imports `@AGENTS.md`
     when that file exists or is generated), a nested `CLAUDE.md` per unit (Claude Code loads it when working
     there — `@AGENTS.md` when both targets are on, the facts inline otherwise), and — when `home` is not
     `.claude` — a managed stub per skill under `.claude/skills/` so Claude Code still lists it.
   - `agents-md`: root `AGENTS.md` with the overview and an index of nested files (and the facts of a root
     module), a nested `AGENTS.md` **for every owner-doc unit** with a short facts block (dependencies,
     dependents, tests, hotspots, generated code → skill) and a link to the owner doc. Existing files get the
     block appended, the rest is untouched.
3. **Proximity files are projections**: their blocks are regenerated from the same model as the owner doc's
   facts block; the owner doc stays the place for detail and for human text. Every runtime with proximity
   loading gets the measured facts where the work happens.
4. **Outcome honesty**: only Claude Code has hooks. With `claude` not among the targets `apply` prints a note
   that no labels are collected — the harness is still created (ADR-0008 forbids Sherpa's omission of the
   signal, not a runtime's lack of hooks).
5. `adopt` (M3c) reads AGENTS.md hierarchies and `.agents/` as an existing harness the same way as `.claude/`.

## Reasoning
- Proximity loading is what the market converged on; measured, self-updating content in those files is what it
  lacks. Sherpa supplies the second without fighting the first.
- `.agents/` is the only home that two ecosystems already read (Codex skills, the AGENTS.md family) and that no
  runtime owns; `.claude/` stays available for teams that are Claude-only and want one directory.
- Asking when both directories exist — or none — beats guessing: the answer decides where every fact lives
  for years; a single existing directory is the team's answer already.
- Stubs instead of duplicates keep one owner per skill; the stub is a managed file and never edited.

## Consequences
- `Renderer` = core + `claude_targets()` + `agents_md_targets()`; `[apply]` section in `sherpa.toml`; `home`
  and `targets` in the state schema; the checker scans `.agents/**`, every `CLAUDE.md` and `AGENTS.md`.
- A five-module repo with both targets gets 18 files instead of 10 — three of them per unit are proximity files
  of a few lines. A 122-module repository: 243 files, rendered and compared in 0.2 s.
- Further adapters (Cursor `.cursor/rules/*.mdc` with `globs`, Copilot `.github/instructions/*.instructions.md`
  with `applyTo`) are new `targets` values; nothing in the core changes for them.
- Changing `home` later moves every core file: `status` shows the old ones as orphans; a `sherpa move` is a
  candidate once a corpus repo needs it.
