# 08 · Modules: the source tree of `src/sherpa/` and who calls whom

Owner: [plan §2](../plan.md) (architecture), the docstring at the top of each module (its job), ADR-0003
(measurements through `gitinfo`), ADR-0004 (model access only through `sherpa/llm/`, not yet a module),
ADR-0015 (runtime adapters in `render.py`), ADR-0017 (index files through `atomic`), ADR-0042 (schema
validation on every reader). One box per module; the arrows are imports that carry a call, not every import.
The other pages show the mechanics; this one shows where each mechanic lives.

```mermaid
flowchart LR
    user(("repository owner"))

    subgraph cli_group["command layer"]
        cli["cli.py<br/>argparse, one cmd_* per command, exit codes"]
        doctor["doctor.py<br/>every prerequisite with a fix"]
        update["update.py<br/>self-update, the daily hint"]
    end

    subgraph scan_group["scan — deterministic, no LLM"]
        scan["scan/__init__.py<br/>orchestrates T0 and T1"]
        t0["scan/t0_git.py<br/>T0: churn, hotspots, windows"]
        t1["scan/t1_modules.py<br/>T1: manifests to units, coupling"]
        generators["scan/generators.py<br/>generator families, noise globs"]
        model[("model.py<br/>.sherpa/codebase-model.json")]
    end

    subgraph plan_group["plan — rules and thresholds"]
        plan["plan/__init__.py<br/>Plan, Entry, decisions"]
        rules["plan/rules.py<br/>rank, floor, reach, the reasoned no"]
        yamlio[("plan/yamlio.py<br/>.sherpa/harness-plan.yaml, kept decisions")]
    end

    subgraph apply_group["apply — render and write"]
        apply["apply/__init__.py<br/>preview, compare-and-swap, rollback, uninstall"]
        render["apply/render.py<br/>core targets + one adapter per runtime"]
        adopt["apply/adopt.py<br/>terraform import: take over, rebuild, cover"]
        state[("apply/state.py<br/>.sherpa/state.json, the rebuildable index")]
    end

    subgraph integrity_group["integrity"]
        check["check.py<br/>rules C1–C8, stdlib only, deployed as a copy"]
        status["apply/status.py<br/>drift, findings, outcome labels"]
    end

    harness["the harness in the user's repository<br/>{home}/**, CLAUDE.md, AGENTS.md — see 07"]
    pypi["PyPI · GitHub releases"]

    user --> cli
    cli --> scan & plan & apply & adopt & status & check & doctor & update
    user -. "accept / reject in the YAML" .-> yamlio

    scan --> t0 & t1 & generators
    t1 --> t0
    scan --> model
    model --> rules --> plan --> yamlio
    yamlio --> apply
    apply --> render & state & check
    adopt --> render & state & check
    status --> state & check
    render --> harness
    adopt -. "reads" .-> harness
    doctor --> update --> pypi

    subgraph cross_group["cross-cutting — no arrows drawn, every layer uses them"]
        config["config.py<br/>sherpa.toml, TARGETS, HOMES<br/>← scan, plan, apply, render, doctor"]
        gitinfo["gitinfo.py<br/>origin/&lt;trunk&gt;, nested repositories<br/>← cli, scan, adopt, doctor"]
        atomic["atomic.py<br/>write-rename for every index file<br/>← yamlio, state, apply, update"]
        schema["schema.py<br/>validates model, plan, state on read<br/>← model, yamlio, state"]
    end
    harness ~~~ cross_group
```

What to remember:

- **`check.py` imports nothing from the package**: it is copied into `{home}/scripts/sherpa-check.py` and runs
  under `python -I -S`; everything else may import it. The one exception is the deployed copy handing over to
  an installed, never older `sherpa.check` when it finds one.
- **Every Git measurement goes through `gitinfo`** (ADR-0003), every index file through `atomic` (ADR-0017),
  every read of a `.sherpa/` file through `schema` (ADR-0042) — three modules, three invariants.
- **`render.py` is the only place that knows a runtime** (ADR-0015): the core targets and both adapters,
  `claude` and `agents-md`, are equal citizens there; the core, `apply` and `adopt` see only `home`.
- **`cli.py` composes, it does not compute**: parsing, the questions on a terminal, exit codes — the result of
  a command is built in its module and rendered there (`apply.render_result`, `status.render`).
