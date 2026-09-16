# Sherpa

Generischer Harness-Generator. CLI `sherpa` (`scan | plan | apply | status`), Python 3.12, stdlib-first.
Plan und Architektur: `docs/plan.md`. Scanner: `docs/scan.md`. Entscheidungen: `docs/adr/`. Feldsemantik: `src/sherpa/schemas/`.

## Regeln
- Owner-Prinzip: jede Tatsache hat genau einen Ort. `docs/plan.md` besitzt Architektur und Meilensteine,
  ADRs besitzen Entscheidungen, Code besitzt Verhalten. Keine Duplikate in README oder Kommentaren.
- Scanner und Applier bleiben deterministisch (kein LLM, keine Netzabhängigkeit). LLM nur in `plan`.
- Jede erzeugte Datei trägt den `sherpa:generated`-Marker; handbearbeitete Dateien werden nie überschrieben.
- Tests: `.venv/bin/pytest -q` aus der Repo-Wurzel. Jede neue Funktion kommt mit Tests; Fixture-Repos werden
  programmatisch gebaut (`tests/conftest.py`), nie als Binärdaten eingecheckt. Coverage-Ziel ≥ 90 % (`docs/plan.md` §5).
- Git-Messungen immer gegen `origin/<trunk>` via `sherpa.gitinfo.resolve_trunk` (ADR-0003), nie gegen `HEAD`.
- Sprachunabhängig: T0 (Git) und T1 (Manifeste) müssen ohne Sprach-Adapter funktionieren (`docs/plan.md` §2.1).
- Modell-Zugriff nur über `sherpa/llm/` (ADR-0004); kein LangChain/LangGraph, kein Provider-Code ausserhalb.
- Nicht committen, ausser Andrei sagt es.
- Sprache in Docs und Commits: Deutsch.

## Produkt, nicht Projekt
- Sherpa ist generisch. Docs, Code, Tests und Beispiele nennen **kein** konkretes Kundenprojekt beim Namen; Beispiele
  verwenden neutrale Namen (`Shop.Pricing`). Das Referenz-Harness ist ein Datenpunkt (ADR-0002), nicht die Wahrheit.
- Fremde Repos werden nur lokal zum Testen gescannt (`tests/corpus/`, ignored); ihre Modelle werden nicht eingecheckt.

## Zusammenarbeit
- Team-Arbeit: bei Unsicherheit oder Design-Entscheidungen Andrei fragen, nicht still entscheiden. Was getan wurde,
  wird knapp berichtet — er muss jederzeit wissen, was passiert.
