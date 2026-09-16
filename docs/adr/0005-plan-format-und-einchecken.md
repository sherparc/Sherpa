# ADR-0005 — Plan-Datei als YAML; Plan und State werden im Zielrepo eingecheckt, das Modell nicht

**Status:** akzeptiert · **Datum:** 2026-09-16 · **Entscheid:** Andrei (Format an Claude delegiert)

## Kontext
`sherpa plan` erzeugt eine Datei, die ein Mensch bei der Freigabe **liest und editiert** (`default: propose` →
`accept`/`reject`). `sherpa apply` schreibt einen State, der beim nächsten Lauf sagen muss, was Sherpa erzeugt hat
und was handbearbeitet wurde. Beides lebt im Zielrepo unter `.sherpa/`.

## Entscheidung
1. **`.sherpa/harness-plan.yaml`** — YAML, gelesen und geschrieben mit PyYAML (`safe_load`/`safe_dump`, sortierte
   Schlüssel, feste Einrückung). Erste und vorerst einzige Laufzeit-Abhängigkeit von Sherpa.
2. **`.sherpa/state.json`** — JSON (stdlib). Wird von Maschinen geschrieben, von Menschen nur gelesen.
3. **Eingecheckt** im Zielrepo: `harness-plan.yaml` und `state.json`. **Nicht** eingecheckt:
   `codebase-model.json` (reproduzierbar aus `origin/<trunk>`-Rev). `sherpa apply` legt dafür
   `.sherpa/.gitignore` mit `codebase-model.json` an.

## Begründung
- Die Freigabe ist der Moment, in dem der Mensch den Plan anfasst. YAML mit Kommentaren (`# Kippkriterium: …`)
  ist dafür lesbar; JSON ohne Kommentare und mit Anführungszeichen-Pflicht ist es nicht.
- Plan und State sind das, was ein Reviewer im PR sehen muss („welche Harness-Teile kommen dazu, was wurde
  freigegeben"). Terraform-Praxis: State ohne Versionierung führt zu Drift, den niemand sieht.
- Das Modell ist gross (Referenz-Repo: 15 134 Datei-Einträge) und bei gleichem Rev byte-identisch — Einchecken
  würde nur Diff-Rauschen erzeugen.
- Stdlib-first (ADR-0001) bleibt der Grundsatz; PyYAML ist die eine begründete Ausnahme, weil das Format eine
  Produktentscheidung ist, keine Bequemlichkeit.

## Konsequenzen
- `pyproject.toml`: `dependencies = ["pyyaml>=6"]`.
- Plan-Schema als JSON-Schema (`src/sherpa/schemas/harness-plan.schema.json`); YAML wird nach dem Laden dagegen
  validiert — das Format ändert nichts an der Prüfung.
- Determinismus: `safe_dump(sort_keys=True, allow_unicode=True, width=120)` — zwei Läufe, gleiche Bytes.
