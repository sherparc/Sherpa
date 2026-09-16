# ADR-0007 — Bestehende Harnesse werden per `sherpa adopt` übernommen, nie überschrieben

**Status:** akzeptiert · **Datum:** 2026-09-16 · **Entscheid:** Andrei (Plan-Revision 2)

## Kontext
Zielrepos haben oft schon ein `.claude/` (Referenz-Repo: 17 Agents, 5 Librarians). Ein `apply`, das nur „neu
anlegen" kennt, könnte dort nicht laufen oder würde Handarbeit zerstören. Terraform löst dasselbe Problem mit
`import`: bestehende Ressourcen kommen in den State, ohne verändert zu werden.

## Entscheidung
Eigenes Kommando `sherpa adopt` (Details `docs/plan.md` §2.6): klassifiziert `.claude/**`, schreibt jede Datei
als `origin: adopted, hand-edited: true` in den State, verknüpft sie mit Modulen des Modells und meldet Lücken als
Plan-Einträge. `apply` fasst adoptierte Dateien nie an; `status` behandelt sie wie handbearbeitete.

## Begründung
- Ohne Adopt ist Sherpa nur für Greenfield-Repos brauchbar — die Minderheit.
- Adopt macht das Referenz-Repo zum ausführbaren Regressionsfall (§3): dieselbe Analyse, die heute von Hand läuft.
- Trennung von `apply` hält `apply` rein deterministisch; `adopt` ist Lesen + State-Schreiben.

## Konsequenzen
- State-Schema bekommt `origin: generated | adopted` und `hand-edited`.
- Klassifikation über Pfad + Frontmatter; Unbekanntes wird `kind: unknown` und im Report genannt, nie geraten.
- Teil von M3.
