# ADR-0050 — Host breadth is a goal: one thin adapter per agent runtime, not one per corpus request

**Status:** accepted · **Date:** 2026-09-19 · **Deciders:** Andrei · **Amends:** ADR-0015 §2 (the target set
grows beyond `claude` and `agents-md`), ADR-0023 (Hermes is the first of a row, not the exception), plan Q8
(the gate "once a corpus repository uses them" is dropped)

## Context

ADR-0015 made the harness runtime-neutral and ADR-0023 added Hermes as the third target; Codex, Cursor and
Copilot were to follow "when a corpus repository uses them" (plan §0, Q8). On 2026-09-19 a comparison with
metaharness (ruvnet, MIT, v0.1 beta, ~660 stars) showed what the market reads as breadth: it lists ten hosts —
Claude Code, Codex, pi.dev, Hermes, OpenClaw, RVM, Copilot, OpenCode, GitHub Actions, Prime Agent — as
adapters of one generated package. Its product is a different one (a scaffold for a *new* branded harness
package with its own CLI and MCP server; static analysis of manifests, no git history, no reasoned no's, no
in-place adoption, no outcome channel), but the first question a reader asks both projects is the same: "does it
work with my runtime?" Sherpa's honest answer today is "Claude Code natively, everything that reads `AGENTS.md`
through the neutral core" — true, and invisible in a host list of two.

## Decision

1. **Host breadth is a milestone of its own (M3k), placed right after M3h.** The gate "a corpus repository uses
   it" is dropped; the gate is the host's documented contract. First row: `codex`, `opencode`, `copilot`,
   `cursor`, `gemini`. Hosts that read `AGENTS.md` and `.agents/skills` and have nothing else of their own get
   no adapter — they are covered by `agents-md`, and `doctor` says so by name.
2. **Every adapter is thin on top of `agents-md`, exactly like `hermes` (ADR-0023).** An adapter may add three
   things and nothing else: (a) **detection** — a `doctor` line naming the host when its marker is present
   (`.codex/`, `.opencode/`, `.github/copilot-instructions.md`, `.cursor/`, `.gemini/` or `GEMINI.md`, the
   binary on the `PATH`) and the default target set following the detection as in ADR-0015; (b) **the host's
   native rule file** where the host has one and it carries something `AGENTS.md` cannot — Cursor's
   `.cursor/rules/*.mdc` with `globs`, Copilot's `.github/instructions/*.instructions.md` with `applyTo`,
   Gemini's `GEMINI.md` when the host is not configured to read `AGENTS.md` — always as a managed block or a
   managed file that imports or repeats the proximity facts, never a second source of truth; (c) **the outcome
   hook** where the host has hooks with a JSON-on-stdin contract, one script for all payload shapes as in
   ADR-0023; a host without hooks gets ADR-0015 §4's note.
3. **Facts before code.** Each adapter starts with a one-page contract note under `docs/concepts/hosts/` —
   what the host loads, from where, in which precedence, which hook events exist — verified against the host's
   documentation or source on a dated line, the way §9 did for Hermes. An adapter whose contract cannot be
   verified is not built.
4. **`[apply] targets` and the state keep their shape**; `TARGETS` grows, unknown names are refused as today.
   The plugin milestone (M7a) stays Claude Code plus Hermes; further plugin hosts are decided after M3k on the
   evidence of which adapters are used.

## Reasoning

- Breadth is cheap here and expensive elsewhere: the neutral core exists, `hermes` is the template, and each
  adapter is detection plus at most one file kind plus a hook branch. What metaharness buys with a Rust kernel
  and ten adapters, Sherpa gets from the `AGENTS.md` convention plus a thin layer per host.
- Waiting for a corpus repository to use Cursor or Copilot measured the wrong thing: the corpus is four
  open-source repositories chosen for their ecosystems, not for their agent runtimes.
- The three-thing limit keeps adapters from becoming what ADR-0015 forbids — a runtime-specific harness. Anything
  beyond detection, one native file and one hook branch is a plan question, not an adapter feature.

## Consequences

- Plan §3 gets M3k with its acceptance; the README roadmap mirrors it and the README names the hosts and the
  neighbour project under `## Related`.
- `doctor` grows one informational line per detected host; `TARGETS` and the target docs grow per adapter.
- M5 moves one slot back. §9's argument for M5 early (prove the claim before the market asks) is not dropped —
  a wider row of hosts collects more outcome labels for it where the hosts have hooks.
