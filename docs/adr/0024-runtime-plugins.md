# ADR-0024 — Runtime plugins: Sherpa installable inside Claude Code and Hermes, thin, from one source

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei

## Context

Sherpa is a CLI. Its users already live in an agent runtime, and both runtimes Sherpa targets have a
distribution channel of their own: Claude Code installs plugins (`.claude-plugin/plugin.json` with `commands/`,
`agents/`, `skills/`, `hooks/hooks.json`; a marketplace is a repository with `.claude-plugin/marketplace.json`,
`claude plugin install <name>@<marketplace>`), Hermes installs skills and bundles (`hermes skills install`,
`hermes skills tap add owner/repo` for a registry, `hermes bundles create` to group skills under one command).
Q9 already moved interactive per-entry approval out of the CLI into the runtime ("`/sherpa-plan` in Claude Code
is the better place"), and M7 names that command.

## Decision

1. Milestone **M7a — runtime plugins**, after M3h and before M5: a Claude Code plugin and a Hermes skill bundle,
   generated from **one source** in this repository (`plugins/` — the plugin manifest, the command and skill
   texts), released with every tag next to the wheel.
2. The plugins are **thin**: every command (`/sherpa-plan`, `/sherpa-apply`, `/sherpa-status`, `/sherpa-doctor`)
   calls the installed CLI and presents its output; the runtime adds what the CLI refused by design — reading
   the plan entry by entry and asking, then writing the decision with `sherpa plan --accept/--reject` (M3d).
   No rule, no measurement and no file rendering lives in a plugin. If the CLI is missing, the command says how
   to install it (`uv tool install …`) and stops.
3. The **outcome hook stays with `apply`** (ADR-0008): the plugin ships no hook of its own, because a label
   needs the `harness_rev` from `.sherpa/state.json` and a second hook would count every execution twice.
4. Versioning: the plugin's version equals the wheel's; `release.yml` publishes both, `doctor` reports a plugin
   older than the CLI as a hint.

## Reasoning

- Users install Sherpa where they already are; one command instead of a second CLI to learn. Hermes' skills hub
  and Claude Code's marketplace are the two channels with reach today.
- Thin plugins keep determinism and tests in the CLI (ADR-0001, plan §5) and make the plugin trivially
  regenerable; a fat plugin would be a second product with a second test suite.
- One source for both keeps the texts in step — the same discipline as the owner docs (one owner per fact).

## Consequences

- New directory `plugins/` with a generator script and a test that the generated plugin manifests are valid;
  `release.yml` attaches them; `docs/getting-started.md` gets an "install inside your runtime" section.
- `/sherpa-plan` in M7 is delivered by M7a; M7 keeps librarians and multi-repo.
- Rejected: business logic in the plugin; a hook in the plugin; separate sources per runtime.
