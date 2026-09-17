# 01 · Scan: two tiers of facts, one model

Owner: [concepts/scan](../concepts/scan.md). T0 needs only Git and works on every repository; T1 needs
manifests and gives module boundaries; language adapters (M3b) would be a T2 and are not built.

```mermaid
flowchart TB
    subgraph T0["T0 · Git (ADR-0003, ADR-0038)"]
        trunk["resolve_trunk<br/>origin/HEAD → candidate → override"]
        lsfiles["ls-tree -z<br/>every path at trunk"]
        log["log -z --no-merges --since=90d<br/>sha, author, date, paths — NUL-separated"]
        blobs["cat-file --batch<br/>LOC per text file, None for binaries"]
        trunk --> lsfiles & log & blobs
    end
    subgraph T1["T1 · manifests (ADR-0002)"]
        manifests["*.csproj, pyproject.toml, package.json,<br/>go.mod, Cargo.toml, pom.xml, build.gradle"]
        owner["owner(path) = deepest module<br/>whose directory contains it"]
        manifests --> owner
    end
    generated["generator families<br/>migrations, protobuf, OpenAPI, snapshots, lockfiles<br/>excluded from hotspots"]
    modules["modules[]<br/>files, LOC, commits 90d/30d, authors,<br/>deps, dependents, sub_dirs"]
    hotspots["git.hotspots[]<br/>commits_90d × LOC, text only"]
    coupling["modules[].coupling[]<br/>partners that changed in the same commits<br/>shared, share, of (ADR-0021, 0026, 0039)"]
    cap["size cap = max(5, modules/2)<br/>squash merges and mass renames skipped<br/>root catch-all excluded"]
    model[("codebase-model.json<br/>sorted keys, byte-stable")]

    lsfiles --> owner
    log --> modules & hotspots & coupling
    blobs --> hotspots & modules
    owner --> modules
    lsfiles --> generated --> hotspots
    cap --> coupling
    modules & hotspots & coupling --> model
```

What to remember:

- **Measured against `origin/<trunk>`, never `HEAD`** — a local branch or a dirty worktree changes nothing.
- **Coupling's denominator is the measured commits**, not `commits_90d`: the row in an owner doc prints both
  numbers it was computed from (`6 of 12 measured commits, 50 %`).
- **Unusual paths are data, not quoting**: `-z` everywhere, so `über.py` in `log` equals `über.py` in `ls-tree`.
