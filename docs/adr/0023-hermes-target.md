# ADR-0023 — Hermes Agent as the third target, and the first step towards runtime independence

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei

## Context

The plan's direction beyond the milestone table (§0) is independence from any single agent runtime. Building a
runtime is the slice where a one-person product loses against Claude Code and Hermes Agent; what neither runtime
has is the measured, reviewable, runtime-neutral harness layer Sherpa builds (plan §9).

Hermes Agent (Nous Research, open source, multi-provider, local models) reads exactly what Sherpa already
writes. Measured against its documentation on 2026-09-17:

- Context: a merged chain of `AGENTS.md` files from the git root down to the working directory, nested files
  discovered progressively; `CLAUDE.md` as a fallback. Precedence per session, first match wins:
  `.hermes.md`/`HERMES.md` → `AGENTS.override.md` → `AGENTS.md` → `CLAUDE.md` → `.cursorrules`.
- Skills: `<root>/.agents/skills/*/SKILL.md` (or `.hermes/skills/`), agentskills.io layout, `version` in the
  front matter required, project skills loaded only after `hermes skills trust`.
- Hooks: shell hooks with JSON on stdin (`hook_event_name`, `cwd`, `session_id`, `tool_name`) for
  `post_tool_call`, `on_session_end`, `agent_loop_stopped` and others — registered **globally** in
  `~/.hermes/config.yaml`, never in the repository.

Sherpa's `agents-md` target and `home: .agents` therefore serve Hermes today with no change; the gaps are the
skill front matter, the `.hermes.md` precedence trap, the outcome hook's wiring and `doctor`'s blindness to Hermes.

## Decision

1. `hermes` becomes the third entry of `TARGETS` (ADR-0015: a new runtime is a new adapter in `apply/render.py`,
   never a change to the core). It is selected like the others: `sherpa.toml [apply] targets`, else the state,
   else detected — `hermes` on the `PATH`, `~/.hermes/`, or `.hermes.md`/`HERMES.md` in the repository.
2. The adapter is thin by design. With `agents-md` active it adds no file; when `.hermes.md`/`HERMES.md` exists
   it appends the root block there (ADR-0016: append, never overwrite), because Hermes would otherwise not
   load `AGENTS.md` at all. Without `agents-md` it writes the root `AGENTS.md` block and the nested files itself.
3. `version: 1` enters every skill's front matter in the **neutral core** — agentskills.io allows it, Claude
   Code ignores it, Hermes requires it. Existing skills get it through the block/adopt path like any rendering
   change (ADR-0022 pattern list).
4. The outcome channel keeps its mandatory minimum (ADR-0008) with a split: the hook script is deployed into
   the repository as today (`<home>/hooks/sherpa-outcome.py`, one script, both payload shapes), the **wiring**
   is a user action because Hermes has no project-local hooks. `apply` prints the `config.yaml` snippet once;
   `doctor` gets a check `hermes-hook` (ok / hint with the snippet) and a check `hermes-trust` for
   `skills.trusted_project_dirs`. `status` counts outcome labels from both runtimes in one table, keyed by
   `harness_rev`.
5. The runtime direction in §0 stays, reordered: independence is reached first through open runtimes (Hermes
   now, Codex/Cursor/Copilot adapters as the corpus demands), and only then — if at all — through an executor
   of Sherpa's own for evals and librarians. No chat runtime of its own.

## Reasoning

- A day of adapter work puts Sherpa's harness in front of Hermes' user base; a runtime of its own would compete
  with it. Terraform never replaced a cloud; it became what every cloud needs.
- Everything Hermes needs is already the neutral format (nested `AGENTS.md`, `.agents/skills`): the decision
  proves ADR-0015 rather than stretching it.
- The global hook is the one thing Sherpa cannot deploy; making it a `doctor` check with a fix follows the
  product's own rule "the message names the way out" instead of pretending the minimum is met.

## Consequences

- Milestone **M3h** (plan §3) before M5; `TARGETS`, `doctor`, `render.py`, the hook script and the docs move.
- The hook script must accept both payloads and both event vocabularies (`PostToolUse`/`Stop` and
  `post_tool_call`/`on_session_end`); one test per runtime shape.
- ADR-0015's "ask when both homes exist" is unchanged; a repository with `.hermes.md` and `.claude/` gets both
  adapters and one core.
- Rejected: writing into `~/.hermes/config.yaml` from `apply` — Sherpa never writes outside the repository.
- Rejected: a `hermes` skills directory of its own — `.agents/skills` is read by Hermes and is the neutral home.
