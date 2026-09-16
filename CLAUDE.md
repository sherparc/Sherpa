# Sherpa

Generischer Harness-Generator. CLI `sherpa` (`scan | plan | apply | status`), Python 3.12, stdlib-first.
Plan und Architektur: `docs/plan.md`. Scanner: `docs/scan.md`. Entscheidungen: `docs/adr/` (Index in `docs/adr/README.md`). Feldsemantik: `src/sherpa/schemas/`.

## Regeln
- Owner-Prinzip: jede Tatsache hat genau einen Ort. `docs/plan.md` besitzt Architektur und Meilensteine,
  ADRs besitzen Entscheidungen, Code besitzt Verhalten. Keine Duplikate in README oder Kommentaren.
- Scanner und Applier bleiben deterministisch (kein LLM, keine Netzabhängigkeit). LLM nur in `plan`.
- Jede erzeugte Datei trägt den `sherpa:generated`-Marker; handbearbeitete Dateien werden nie überschrieben.
- Tests: `.venv/bin/pytest -q` aus der Repo-Wurzel; Lint `.venv/bin/ruff check . && .venv/bin/ruff format --check .` — beides muss vor jedem Commit grün sein (CI prüft Linux, Windows, macOS). Jede neue Funktion kommt mit Tests; Fixture-Repos werden
  programmatisch gebaut (`tests/conftest.py`), nie als Binärdaten eingecheckt. Coverage-Ziel ≥ 90 % (`docs/plan.md` §5).
- Git-Messungen immer gegen `origin/<trunk>` via `sherpa.gitinfo.resolve_trunk` (ADR-0003), nie gegen `HEAD`.
- Sprachunabhängig: T0 (Git) und T1 (Manifeste) müssen ohne Sprach-Adapter funktionieren (`docs/plan.md` §2.1).
- Modell-Zugriff nur über `sherpa/llm/` (ADR-0004); kein LangChain/LangGraph, kein Provider-Code ausserhalb.
- Vor jedem Commit den Diff zeigen (`git diff --stat` + Kernpunkte) und Andrei fragen; erst nach seinem Ja committen und pushen.
- Commit-Messages: 1 bis 3 ganze Sätze, nie ein `Co-Authored-By`-Trailer.
- Sprache in Docs und Commits: Deutsch.

## Produkt, nicht Projekt
- Sherpa ist generisch. Docs, Code, Tests und Beispiele nennen **kein** konkretes Kundenprojekt beim Namen; Beispiele
  verwenden neutrale Namen (`Shop.Pricing`). Das Referenz-Harness ist ein Datenpunkt (ADR-0002), nicht die Wahrheit.
- Fremde Repos werden nur lokal zum Testen gescannt (`tests/corpus/`, ignored); ihre Modelle werden nicht eingecheckt.

## Zusammenarbeit
- Nach jedem Schritt `docs/plan.md` kritisch revidieren: gegen die besten etablierten Marktlösungen (Terraform,
  Backstage, Renovate, CodeScene, promptfoo, …) plus eigenes Wissen — Inkonsistenzen, fehlende Bausteine, bessere
  Alternativen mit Begründung vorschlagen; Andrei entscheidet, was in den Plan kommt.
- Nach jeder Iteration ein ADR je getroffener Entscheidung (`docs/adr/`, Index pflegen). Was kein ADR hat, ist
  nicht entschieden.
- Team-Arbeit: bei Unsicherheit oder Design-Entscheidungen Andrei fragen, nicht still entscheiden. Was getan wurde,
  wird knapp berichtet — er muss jederzeit wissen, was passiert.
