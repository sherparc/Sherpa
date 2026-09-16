# `sherpa scan` — Schichten T0 (Git) und T1 (Module)

> Owner für: Aufruf, Entscheidungen, Interpretation. Feldsemantik gehört dem Schema
> [`src/sherpa/schemas/codebase-model.schema.json`](../src/sherpa/schemas/codebase-model.schema.json) (v2); Code in
> [`src/sherpa/scan/t0_git.py`](../src/sherpa/scan/t0_git.py) und [`t1_modules.py`](../src/sherpa/scan/t1_modules.py).
> Stand: M1a, v0.2.0.

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
| `modules[]` | ein Modul je Manifest: `id`, `path`, `kind`, Dateien/LOC/Testdateien, `deps`/`dependents`/`tested_by` (nur repo-intern), Churn je Modul, bis zu 3 Hotspots | Manifest-Parser (T1) |
| `conventions` | Sprachen nach LOC, CI-Dateien, Container-Dateien | Dateibaum |

### T1 — welche Manifeste, wie werden Abhängigkeiten aufgelöst

| `kind` | Manifest | Modulname | repo-interne Deps über | Test-Erkennung |
|---|---|---|---|---|
| `dotnet` | `*.csproj` `*.fsproj` `*.vbproj` | Dateistamm | `<ProjectReference Include>` → Manifest-Pfad (Backslashes normalisiert, Fallback Dateistamm) | eigenes Test-Projekt: `IsTestProject`, Paket xunit/nunit/mstest/tunit, Name `*Tests`/`*Test` → `is_test`, erscheint bei den referenzierten Modulen als `tested_by` |
| `python` | `pyproject.toml` `setup.py` | `[project].name` / `[tool.poetry].name` | Namen aus `dependencies`, `optional-dependencies`, Poetry-Gruppen, PEP-503-normalisiert (`Shop_Lib` ≙ `shop-lib`) | Testdateien im Modul |
| `node` | `package.json` | `name` | Schlüssel aus `dependencies`/`devDependencies`/`peerDependencies` | Testdateien im Modul |
| `go` | `go.mod` | `module` | `require`-Zeilen und `replace`-Ziele, exakter Modulpfad | `*_test.go` |
| `rust` | `Cargo.toml` mit `[package]` (reiner `[workspace]` ist kein Modul) | `package.name` | `path = "…"`-Deps → Manifest-Pfad; sonst Name | Testdateien im Modul |
| `java` | `pom.xml` `build.gradle(.kts)` | `<artifactId>` (Gradle: Verzeichnisname) | `<dependency><artifactId>` gegen andere Module | `*Test.java`, `src/test/` |

Manifeste unter `node_modules/`, `vendor/`, `target/`, `bin/`, `obj/`, `dist/`, `build/`, `.venv/`, `packages/`
sind keine Module. Zwei Manifeste im selben Verzeichnis (z. B. `package.json` neben `pyproject.toml`): das
alphabetisch erste gewinnt — bewusst simpel, wird ein Kippkriterium, falls ein Korpus-Repo es braucht.

Externe Pakete (`requests`, `serde`, `react`) tauchen **nicht** in `deps` auf: für Owner-Grenzen zählt nur, was im
Repo lebt. Testdateien = Pfad enthält `tests/`, `test/`, `__tests__/`, `spec/` oder Name matcht `test_*.py`,
`*_test.go`, `*.test.ts`, `*.spec.js`, `*Test.java`, `*Tests.cs`, `*_test.rs`, ….

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
8. **Jede Datei gehört zum tiefsten Modul** (längster Manifest-Pfad, der Präfix ist). Ein Wurzel-Manifest
   fängt den Rest. Dateien ohne Modul (`docs/`, `.github/`, `Dockerfile`) zählen in `git.dirs`, aber in keinem Modul.
9. **Modul-Churn zählt je Commit einmal.** Ein Commit, der 40 Dateien eines Moduls berührt, ist ein Commit —
   sonst gewinnen Refactorings jede Rangliste. Datei-Churn (`git.files`) bleibt daneben erhalten.
10. **Sprach-Adapter (T2) sind optional.** T1 liest Manifeste, keinen Code. Referenz-Repo: 48 Module (46 dotnet,
    2 node), `tested_by` korrekt über `ProjectReference`, 2,6 s.

## Interpretation für `plan` (M2)

- `dirs[].commits_90d` / `commits_30d` gegen die Schwellwerte in `docs/plan.md` §2.2 → Librarian-/Agent-Kandidaten.
- `hotspots` → Owner-Doc-Abschnitt „Wo brennt es", Eval-Frage „Welche Datei ist der Hotspot in X?".
- `authors_90d` = 1 bei hohem Churn → Bus-Faktor-Hinweis, Owner-Doc dringender.
- `dirs` mit `path` unter `tests/` und hohem Churn → Test-Infrastruktur als eigener Bereich (blinder Fleck laut
  Analyse-Praxis: oft mehr Commits als jedes Fachmodul, niemand betreut sie).
