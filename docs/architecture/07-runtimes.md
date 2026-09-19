# 07 · Runtimes: one neutral core, one adapter per target

Owner: ADR-0015 (core under `home`, adapters), ADR-0023 (the `hermes` target, M3h), ADR-0050 (host breadth:
one thin adapter per runtime, M3k), ADR-0024 (runtime plugins, M7a). `home` is `.claude` when Claude Code is
the runtime, `.agents` otherwise; a new runtime is a new adapter in `apply/render.py`, never a change to the
core — and every adapter after `claude` is thin on top of `agents-md`.

```mermaid
flowchart LR
    plan[("harness-plan.yaml<br/>selected entries")]
    subgraph core["core targets — runtime-neutral, under {home}"]
        docs["{home}/docs/modules/&lt;unit&gt;.md<br/>owner doc, block facts (+ graph in M3g)"]
        skills["{home}/skills/&lt;name&gt;/SKILL.md<br/>procedures, e.g. regenerate-&lt;family&gt;"]
        librarian["{home}/skills/&lt;unit&gt;-sync/SKILL.md<br/>librarian"]
        checker["{home}/scripts/sherpa-check.py<br/>a copy of sherpa/check.py, stamped"]
        ignore[".sherpa/telemetry/.gitignore"]
    end
    subgraph claude["adapter: claude"]
        agents[".claude/agents/&lt;unit&gt;.md<br/>role + knowledge manifest, blocks knowledge, manifest"]
        hook[".claude/hooks/sherpa-outcome.py"]
        settings[".claude/settings.json<br/>json-hooks merge: four entries"]
        claudemd["CLAUDE.md, &lt;unit&gt;/CLAUDE.md<br/>block harness, appended"]
    end
    subgraph agentsmd["adapter: agents-md"]
        rootagents["AGENTS.md<br/>block harness, appended"]
        unitagents["&lt;unit&gt;/AGENTS.md<br/>block facts, proximity budget (ADR-0029)"]
    end
    subgraph hermes["adapter: hermes (M3h, planned)"]
        hermesmd[".hermes.md / HERMES.md<br/>root block on top of agents-md"]
    end
    subgraph thin["adapters: codex · opencode · copilot · cursor · gemini (M3k, planned)"]
        detect["doctor: names the host<br/>.codex/, .opencode/, .github/copilot-instructions.md, .cursor/, .gemini/ or GEMINI.md"]
        native["native rule file only where AGENTS.md cannot carry it<br/>.cursor/rules/*.mdc (globs) · .github/instructions/*.instructions.md (applyTo) · GEMINI.md"]
        thinhook["outcome hook where the host has hooks<br/>one script, every payload shape"]
    end
    plan --> core
    plan --> claude
    plan --> agentsmd
    plan -.-> hermes
    plan -.-> thin
    agentsmd -. "carries the facts for" .-> hermes & thin
    settings -. "wires" .-> hook
    agents -. "knowledge.always → " .-> docs
```

What to remember:

- **Facts live once, in the owner doc**; agents carry a role and a manifest that points at facts, never facts.
- **Outcome labels need a runtime with hooks**; `apply` says so when `claude` is not among the targets.
- **Every further adapter adds at most three things** (ADR-0050): detection in `doctor`, the host's native rule
  file where `AGENTS.md` cannot carry it (as a managed block, never a second source of truth), and the hook
  where the host has one. Facts before code: a contract note under `docs/concepts/hosts/` comes first.
- **Both homes present and nothing decided** → `apply` asks on a terminal and refuses otherwise; `sherpa.toml
  [apply]` beats the state beats detection.
