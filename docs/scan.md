# `sherpa scan` — Schicht T0 (Git)

> Owner für: Aufruf, Entscheidungen, Interpretation. Feldsemantik gehört dem Schema
> [`src/sherpa/schemas/codebase-model.schema.json`](../src/sherpa/schemas/codebase-model.schema.json); Code in
> [`src/sherpa/scan/t0_git.py`](../src/sherpa/scan/t0_git.py). Stand: M1, v0.1.0.

## Aufruf

```bash
sherpa scan <repo>                      # → <repo>/.sherpa/codebase-model.json
sherpa scan <repo> --out -              # JSON auf stdout
sherpa scan <repo> --no-fetch           # ohne 'git fetch origin' (offline, Tests)
sherpa scan <repo> --trunk dev          # Trunk erzwingen (schlägt sherpa.toml)
sherpa scan <repo> --as-of 2026-03-01   # Fensterende fixieren (Reproduktion alter Stände)
sherpa scan <repo> --top 50             # mehr Hotspots
```

Exit 0 ok, 1 Fehler (kein Repo, kein origin, Trunk unbekannt, ungültiges Datum). Zusammenfassung auf stderr,
Modell nur in die Datei bzw. stdout — damit ist `--out -` pipe-fähig.

Konfiguration in `<repo>/sherpa.toml` (optional, TOML wegen stdlib `tomllib`):

```toml
[scan]
trunk = "dev"                          # ADR-0003 Override
hotspots = 20
generated = ["*.g.cs", "gen/**"]       # ergänzt sherpa.config.GENERATED_DEFAULT
```

## Was gemessen wird

| Feld | Bedeutung | Quelle |
|---|---|---|
| `git.trunk` | `origin/<branch>`, wie bestimmt (`override` / `origin/HEAD` / `candidate`), SHA | ADR-0003 |
| `git.windows` | `as_of` = Committer-Datum des Trunk-Revs (oder `--as-of`); `since_90d`, `since_30d` | — |
| `git.commits_*` | `total` inkl. Merges über die ganze Historie; `90d`/`30d` nur Nicht-Merge-Commits im Fenster | `git rev-list`, `git log --no-merges --since` |
| `git.files[]` | jede Datei im Trunk-Baum: `loc` (null = binär), `generated`, Commits/Autoren im Fenster, `last_change` | `git ls-tree`, `git cat-file --batch` |
| `git.dirs[]` | Tiefe 1 + 2 (`""` = Wurzel): Dateien, LOC-Summe, Commits, die etwas darunter berühren (je Commit einmal) | Aggregat |
| `git.hotspots[]` | Top-N nach `commits_90d × loc`, nur Text, nur nicht-generiert | Tornhill |

## Entscheidungen und warum

1. **Alles aus dem Trunk-Rev, nichts aus dem Working Tree.** Untracked/lokale Änderungen und der ausgecheckte
   Branch beeinflussen das Modell nicht (`test_scan_ignores_local_branch_and_worktree`).
2. **`as_of` = Committer-Datum des Trunk-Revs.** Damit ist der Scan bei gleichem Rev byte-identisch, auch Wochen
   später. `--as-of` nur für Rückblicke.
3. **Committer-Datum überall**, weil `git --since` danach filtert; Autor-Datum wäre bei Rebases irreführend.
4. **Merges zählen nicht in den Fenstern.** Ein Merge berührt alle Dateien des Zweigs und würde Churn verdoppeln.
5. **Im Fenster gelöschte Dateien fehlen im Modell.** Owner-Kandidaten sind nur Dateien, die es noch gibt.
6. **Generierte Dateien sind nie Hotspot.** Erster Lauf auf dem Referenz-Repo (15 134 Dateien, 44 357 Commits,
   2,5 s): die Top-5-Hotspots waren `*.Designer.cs`, `*ModelSnapshot.cs`, `*.resx` — Werkzeug-Rauschen.
   Mit den Default-Globs (639 Dateien markiert) führen Test-Infrastruktur und Fachcode die Liste an.
   Die Dateien bleiben in `files`/`dirs`, damit `dirs.commits_*` ehrlich bleibt.
7. **Ein Prozess pro Git-Aufruf-Art**, keine Schleife über Dateien (`cat-file --batch`, ein `git log`).
   Laufzeit ist Git-IO; Kippkriterium für einen Rust-Kern steht in ADR-0001.

## Interpretation für `plan` (M2)

- `dirs[].commits_90d` / `commits_30d` gegen die Schwellwerte in `docs/plan.md` §2.2 → Librarian-/Agent-Kandidaten.
- `hotspots` → Owner-Doc-Abschnitt „Wo brennt es", Eval-Frage „Welche Datei ist der Hotspot in X?".
- `authors_90d` = 1 bei hohem Churn → Bus-Faktor-Hinweis, Owner-Doc dringender.
- `dirs` mit `path` unter `tests/` und hohem Churn → Test-Infrastruktur als eigener Bereich (blinder Fleck laut
  Analyse-Praxis: oft mehr Commits als jedes Fachmodul, niemand betreut sie).
