# 04 · The write path: preview, confirm, compare-and-swap, atomic, rollback

Owner: ADR-0030 (compare before the swap), ADR-0031 (symlinks), ADR-0032 (atomic writes and rollback),
ADR-0017 (index files through `sherpa.atomic`). Between the preview and the write sits a human — and possibly
an editor, a second agent, a `git pull`.

```mermaid
sequenceDiagram
    participant U as user
    participant A as sherpa apply
    participant D as repository (disk)
    participant C as checker
    participant S as state.json

    A->>S: load index
    A->>D: read every target (old)
    A->>A: plan_files → actions (+ ~ = !) from old + record
    A-->>U: preview
    U->>A: apply? [y/N]  (or --yes / --dry-run)
    A->>C: FAILs before (baseline)
    loop every action with new bytes
        A->>D: re-read — a symlink in the path?
        alt file still reads as old
            A->>D: atomic write (tmp + rename) — whole or not at all
        else changed since the preview
            A->>A: skip, keep the previous record
        end
    end
    alt OSError half-way
        A->>D: roll back every written file to old (or remove it)
        A-->>U: error + the paths a failed rollback left
    else all written
        A->>C: run all rules
        alt new FAIL that was not in the baseline
            A->>D: roll back
            A-->>U: the new findings, nothing kept
        else
            A->>S: harness_rev over all hashes, applied_at, home, targets — atomic
            A-->>U: n files written · harness_rev …
        end
    end
```

What to remember:

- **`new` was computed from `old`**; if the file is not `old` any more, writing `new` would destroy a stranger's
  bytes. The check is a byte comparison, not a lock — two concurrent `apply` runs skip each other's files.
- **A rollback restores only what this run wrote**; a file skipped since the preview is never touched.
- **The checker is the last gate**: a harness that fails C1–C6 is not written, even after a confirmation.
