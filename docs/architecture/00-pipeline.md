# 00 · The pipeline: from a repository to a harness and back

Owner: [concepts/harness-apply](../concepts/harness-apply.md), [plan §2](../plan.md). Every box is one command;
every cylinder is one file under `.sherpa/`; the harness is the only thing a human or an agent edits.

```mermaid
flowchart LR
    repo[("git repository<br/>origin/&lt;trunk&gt;")]
    scan["sherpa scan<br/>deterministic, no LLM"]
    model[("codebase-model.json<br/>schema v5")]
    plan["sherpa plan<br/>rules + thresholds"]
    planfile[("harness-plan.yaml<br/>decisions live here")]
    apply["sherpa apply<br/>render + write"]
    harness["the harness<br/>AGENTS.md / CLAUDE.md<br/>{home}/docs, skills, agents, hooks"]
    state[("state.json<br/>index: hashes, origin, harness_rev")]
    status["sherpa status<br/>drift, checks, outcomes"]
    adopt["sherpa adopt<br/>rebuild the index from the files"]
    check["sherpa check /<br/>{home}/scripts/sherpa-check.py"]
    hook["outcome hook<br/>labels per execution"]
    outcomes[("telemetry/outcomes.ndjson")]

    repo --> scan --> model --> plan --> planfile --> apply --> harness
    apply --> state
    planfile -. "decision: accept / reject" .-> plan
    harness --> adopt --> state
    state --> status
    harness --> check --> status
    harness --> hook --> outcomes --> status
    model -. "trunk moved? rescan" .-> plan
```

What to remember:

- **Left of `apply` nothing touches the user's repository**; `scan` and `plan` write only under `.sherpa/`.
- **The plan is the contract** (Terraform's saved plan, ADR-0019): `apply` refuses one whose trunk moved.
- **The harness files are the truth, the state is an index over them** (ADR-0017): lose the state, run `adopt`.
- **The loop closes through the hook**: labels carry the `harness_rev` they ran under, so a harness change can
  be measured (M5).
