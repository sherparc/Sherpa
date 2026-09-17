# 05 · State and recovery: the index, and what happens when it is wrong

Owner: ADR-0017 (rebuildable index), ADR-0019 (stale plan), ADR-0034 (no dead end), ADR-0033 (base files after
adopt). Three files can go bad independently; the table below is what each command does with each.

```mermaid
flowchart LR
    subgraph inputs["what a command finds"]
        planOK["plan: fresh"]
        planStale["plan: trunk moved since sherpa plan"]
        stateOK["state: readable"]
        stateTorn["state: torn / foreign schema / missing"]
        modelOld["model: older schema"]
    end
    subgraph verdicts
        planCmd["sherpa plan<br/>rescans the model, drops covered marks<br/>on a torn state, never fails on the index"]
        applyCmd["sherpa apply<br/>refuses a stale plan and a torn state —<br/>it writes from the index"]
        adoptCmd["sherpa adopt<br/>takes a stale plan, rebuilds a torn state<br/>from the files — terraform import"]
        statusCmd["sherpa status<br/>plan: stale as a line, state: unreadable as a line,<br/>drift unknown until rebuilt; exit 1 only on a FAIL"]
    end
    planStale --> applyCmd & statusCmd & adoptCmd
    stateTorn --> planCmd & adoptCmd & statusCmd & applyCmd
    modelOld --> planCmd
    modelOld -. "run sherpa plan (it rescans)" .-> applyCmd & statusCmd
```

The rebuild itself, file by file:

```mermaid
flowchart TB
    file["harness file on disk"] --> render["render the same target from the plan"]
    render --> eq{"equals the rendering<br/>(or an older stamp only)?"}
    eq -- yes --> gen["generated — sherpa's, hash recorded"]
    eq -- "no, blocks" --> blocks{"each block equal?"}
    blocks -- yes --> gen
    blocks -- no --> adoptedB["adopted — yours; the block stays"]
    eq -- "no, base file<br/>checker copy, hook" --> adoptedF["adopted — yours (ADR-0033)<br/>gap line: delete it and apply for a fresh copy"]
    gen & adoptedB & adoptedF --> state[("state.json<br/>same harness_rev as the apply that wrote it")]
    state --> covered["plan: covered marks for adopted files linked to entries"]
```

What to remember:

- **No second way to recover**: `adopt` is the rebuild, `plan` is the rescan; nothing else repairs anything.
- **A rebuild cannot tell a hand edit from an old copy**, so it errs towards yours (ADR-0016 over freshness).
- **The dead end is closed**: torn state plus moved trunk was `plan` → "run adopt", `adopt` → "run plan";
  now `adopt` ignores staleness and `plan` ignores the index it does not own.
