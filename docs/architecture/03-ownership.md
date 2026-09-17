# 03 · Ownership: what `apply` does with a file it meets

Owner: [commands/apply](../commands/apply.md), ADR-0013 (blocks and managed files), ADR-0016 (never
overwrite, only add), ADR-0031 (symlinks), ADR-0033 (base files after adopt). The state record is the only
memory; without one, every byte on disk is somebody's.

```mermaid
flowchart TB
    start(["target path from the plan"]) --> symlink{"symlink anywhere<br/>in the path?"}
    symlink -- yes --> skipS["! never written through"]
    symlink -- no --> adopted{"state record<br/>origin = adopted?"}
    adopted -- yes --> skipA["! yours, never touched<br/>(gone → adopt drops the record)"]
    adopted -- no --> mode{"target mode"}

    mode -- "managed<br/>checker copy, hook, skills" --> mExists{"exists?"}
    mExists -- no --> new1["+ new"]
    mExists -- "yes, no record" --> skipM["! exists, not managed — adopt"]
    mExists -- "yes, record" --> mHash{"hash == record?"}
    mHash -- no --> skipH["! hand-edited"]
    mHash -- yes --> mSame{"same bytes?"}
    mSame -- yes --> unch["= unchanged"]
    mSame -- no --> upd["~ updated"]

    mode -- "blocks<br/>owner docs, agents, AGENTS.md, CLAUDE.md" --> bExists{"exists?"}
    bExists -- no --> new2["+ new"]
    bExists -- "yes, no record, has markers" --> skipB["! markers but no record — adopt"]
    bExists -- "yes, no record, no markers" --> append{"append allowed?"}
    append -- yes --> app["~ block appended<br/>the prose above stays"]
    append -- no --> skipM
    bExists -- "yes, record" --> perBlock["per block: missing → removed by hand<br/>unknown name → not ours<br/>hash differs → hand-edited<br/>else replace inside the markers"]

    mode -- "json-hooks<br/>.claude/settings.json" --> merge["merge sherpa's hook entries,<br/>keep everything else"]
```

What to remember:

- **Three verdicts, no fourth**: `+` create, `~` rewrite only sherpa's own unchanged bytes, `!` leave it — and
  say why. There is no `--force`; the way to a fresh copy is delete and `apply`.
- **Adopted means yours forever** until you delete the file; `apply` will not even report drift on it.
- **Per-block ownership** lets a hand-edited `facts` block coexist with a regenerated `graph` block in one file.
