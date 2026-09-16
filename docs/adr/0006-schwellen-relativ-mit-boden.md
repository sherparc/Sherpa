# ADR-0006 — Plan-Schwellen sind relativ (Perzentil) mit absolutem Boden

**Status:** akzeptiert · **Datum:** 2026-09-16 · **Entscheid:** Andrei (Plan-Revision 2)

## Kontext
Der erste Plan nutzte absolute Schwellen (`commits_90d ≥ 40` für einen Agent). Absolute Zahlen skalieren nicht:
ein Fünf-Personen-Repo mit 200 Commits/Quartal bekäme nie einen Agent, ein Fünfzig-Personen-Repo überall einen.
CodeScene/Tornhill definieren Hotspots deshalb als Perzentile der eigenen Codebasis.

## Entscheidung
- Jede Schwelle = **Rang-Kriterium** (Perzentil oder Top-N über alle Nicht-Test-Module) **und** **Boden**
  (absolute Mindestzahl). Beides muss erfüllt sein.
- Startwerte: Agent = oberstes Quartil nach `commits_90d` ∧ `commits_90d ≥ 20` ∧ `files ≥ 30`;
  Librarian = Top 2 nach `commits_30d` ∧ (`commits_30d ≥ 30` ∨ `commits_90d ≥ 80`).
- Konfigurierbar in `sherpa.toml [plan]`; jede `skip`-Begründung nennt Rang und Boden mit ✓/✗.

## Begründung
Rang allein schlägt in ruhigen Repos an (Top-Quartil von fünf schlafenden Modulen), Boden allein skaliert nicht.
Die Kombination liefert in kleinen wie grossen Repos plausible Vorschläge; die Begründung macht das Kippkriterium
für den Leser rechenbar.

## Konsequenzen
- `plan` braucht die Modul-Rangliste je Kennzahl; sie steht auch im Plan-Header (Nachvollziehbarkeit).
- Test in M2: Fixture mit 5 Modulen ⇒ ≥ 1 Agent; Fixture mit 50 Modulen ⇒ ≤ 13 Agents.
