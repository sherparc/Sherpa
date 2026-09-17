# 06 · The outcome hook: from tool events to one label per execution

Owner: [commands/apply — the outcome hook](../commands/apply.md#the-outcome-hook), ADR-0008 (the minimum),
ADR-0028 (the denominator for M5), ADR-0040 (test runs as command words, the start revision). Stdlib, fail-open,
never prints; one execution is one prompt until the next Stop.

```mermaid
sequenceDiagram
    participant R as runtime (Claude Code)
    participant H as sherpa-outcome.py
    participant S as .sherpa/state.json
    participant O as telemetry/outcomes.ndjson

    R->>H: UserPromptSubmit (prompt)
    H->>S: harness_rev now — the harness the agent starts with
    H->>H: open execution n, signals = 0 — a correction prompt relabels the previous one failed
    loop tools
        R->>H: PostToolUse / PostToolUseFailure (tool, command, failed?)
        alt Bash and a runner is the command word (pytest, uv run pytest, npm test, dotnet test, …)
            H->>H: tests_run += 1, last_test = red or green
        else Bash with gh pr create / git push
            H->>H: pr_created / pushed
        else Edit / Write
            H->>H: edits += 1
        end
    end
    R->>H: Stop
    H->>S: harness_rev again
    H->>O: label = failed if last_test red · success if green or pr_created · unknown otherwise<br/>+ signals, harness_rev (start), harness_rev_at_stop when it moved, 160 chars of prompt
```

What to remember:

- **`unknown` is honest; a false `success` is a wrong number** — hence a runner counts only as the command
  word, never as a word in `cat pytest.ini`.
- **The label belongs to the harness the execution started under**; an `apply` inside the run is recorded as a
  second revision and such records leave the M5 comparison.
- **Nothing leaves the machine**: the ignore file next to the ndjson keeps it out of Git.
