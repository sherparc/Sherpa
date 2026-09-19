# 02 · Plan entries: proposal, decision, coverage, selection

Owner: [concepts/harness-plan](../concepts/harness-plan.md), ADR-0005 (format), ADR-0007 (covered), ADR-0019
(stale plan). The plan is Terraform's model: every proposal unless rejected, every reasoned no unless accepted.

```mermaid
stateDiagram-v2
    direction LR
    [*] --> propose: rule passes its checks
    [*] --> skip: a check fails — the reason is in the plan
    propose --> accepted: decision accept (edit or --accept)
    propose --> rejected: decision reject (edit or --reject)
    skip --> accepted: decision accept
    propose --> covered: adopt links an existing file to the entry,<br/>or the unit's own AGENTS.md sits at its path (ADR-0049)
    covered --> accepted: decision accept — a second file is a decision, never a default
    state "rendered by apply" as rendered
    propose --> rendered
    accepted --> rendered
    rejected --> [*]
    skip --> [*]
    covered --> [*]
```

`selected()` in one line: `decision == accept` **or** (`default == propose` **and** `decision != reject` **and**
not `covered`). Decisions survive a re-plan (`merge_decisions`); `covered` is recomputed from the state on every
plan.

The entry kinds and where their evidence comes from:

```mermaid
flowchart LR
    model[("model")]
    units["units_of<br/>modules, sub-units for a dominant root (ADR-0027)"]
    model --> units
    units --> outcome["outcome<br/>mandatory, one per repo (ADR-0008)"]
    units --> ownerdoc["owner-doc<br/>commits + dependents or files above the floor"]
    units --> agent["agent<br/>rank by churn, commits, files, authors"]
    units --> librarian["librarian<br/>rank by momentum, 30d and 90d floors"]
    units --> testinfra["test-infra<br/>the test directory that names the top unit"]
    model --> skill["skill<br/>generator family with enough generated files and a config"]
    outcome & ownerdoc & agent & librarian & testinfra & skill --> planfile[("harness-plan.yaml<br/>checks with ✓/✗, evidence, cost, reason")]
```

What to remember:

- **Every no has a reason** in the file; a plan a human cannot argue with is not a plan.
- **A typo is refused, not interpreted**: `decision: rejcet` fails validation on every reader (ADR-0042).
- **`apply` refuses a stale plan; `adopt` does not** (ADR-0034) — import needs the resource, not a fresh plan.
