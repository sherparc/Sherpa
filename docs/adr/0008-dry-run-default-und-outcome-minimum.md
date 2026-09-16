# ADR-0008 — `apply` zeigt zuerst den Datei-Diff; Outcome-Minimum ist Teil jedes `apply`

**Status:** akzeptiert · **Datum:** 2026-09-16 · **Entscheid:** Andrei (Plan-Revision 2)

## Kontext
Die Freigabe geschieht auf Plan-Ebene (YAML, ADR-0005), aber der Mensch will vor dem Schreiben sehen, *welche
Dateien* entstehen — `terraform plan` zeigt jede Ressource mit +/−, bevor `apply` wirkt. Zweitens stand der
Outcome-Kanal im Plan als „immer zuerst", war aber Meilenstein M5 nach `apply` (M3) — derselbe Fehler, der im
Referenz-Harness zu 15/15 ungelabelten Ausführungen führte: Signal nach den Features.

## Entscheidung
1. **Dry-Run ist Default.** `sherpa apply` listet jede Datei als `+ neu`, `~ aktualisiert`, `= unverändert`,
   `! hand-edited (übersprungen)` mit Hash und fragt dann. `--yes` überspringt die Frage (CI), `--dry-run` endet
   nach der Liste.
2. **Outcome-Minimum gehört zu `apply`** (M3): Hook-Set, Label-Datei, `harness_rev` = Hash aus Plan + Sherpa-Version.
   Ein Harness ohne Signal wird nicht angelegt. Auswertung (`status`: Labels je `harness_rev`, Trend) folgt in M5.

## Begründung
- Dry-Run macht die Determinismus-Garantie sichtbar: gleiche Liste bei zweitem Lauf = nichts zu tun.
- `harness_rev` ab Tag 0 erlaubt später, Harness-Versionen gegeneinander zu messen; nachträglich ist die
  Zuordnung verloren.

## Konsequenzen
- `apply` hat zwei Phasen: `plan_files()` (rein, testbar) und `write_files()`; Tests prüfen beide getrennt.
- Hook-Set und Label-Format werden generischer Teil der Templates (ADR-0002).
