# ADR-0010 — Lizenz in zwei Stufen: proprietär jetzt, source-available beim öffentlichen Release

**Status:** akzeptiert · **Datum:** 2026-09-16 · **Code:** `LICENSE`, `pyproject.toml`, `README.md`

## Kontext
Sherpa soll später an Firmen verkauft werden, gleichzeitig soll es Reichweite bei Entwicklern bekommen. Ohne
`LICENSE`-Datei gilt „alle Rechte vorbehalten", aber niemand weiss das — und ein Lizenzwechsel ist nur in eine Richtung
möglich: Als alleiniger Urheber kann Andrei jederzeit von proprietär zu offener wechseln; eine einmal unter MIT/Apache
veröffentlichte Version bleibt für immer frei nutzbar. Die Entscheidung muss also *vor* dem ersten öffentlichen
Commit stehen, nicht danach.

Die verbreiteten Modelle passen unterschiedlich gut zum Ziel „Firmen zahlen, Einzelne nutzen frei":

| Modell | Beispiel | Firmeninterne Nutzung |
|---|---|---|
| MIT / Apache (Open Core) | die meisten CLIs | frei; Erlös nur über Zusatzprodukte, die es noch nicht gibt |
| AGPL + kommerzielle Dual-Lizenz | MongoDB (früher) | frei — AGPL greift erst bei Weitergabe/SaaS, nicht bei einem lokal laufenden CLI |
| BUSL 1.1 / FSL | Terraform, Sentry | frei — verboten ist nur ein konkurrierendes Produkt |
| Elastic License 2.0 | Elasticsearch | frei — verboten ist nur der Managed Service |
| PolyForm Small Business 1.0.0 | — | frei bis 100 Personen / 1 Mio. USD Umsatz, darüber Lizenz nötig |
| PolyForm Noncommercial 1.0.0 | — | jede kommerzielle Nutzung braucht eine Lizenz |

## Entscheidung
1. **Jetzt (Repo privat): proprietäre `LICENSE`** — „All rights reserved", Kontakt für kommerzielle Lizenzen und
   Evaluierung. `pyproject.toml` trägt `license = "LicenseRef-Proprietary"`, kein `License ::`-Classifier.
2. **Beim öffentlichen Release: PolyForm Small Business 1.0.0** (Rückfall: PolyForm Noncommercial, falls alle Firmen
   zahlen sollen). Source-available, fertiger Anwaltstext, Docker-Desktop-/JetBrains-Modell: klein und privat frei,
   grosse Firmen kaufen. Das wird ein eigenes ADR, sobald es so weit ist.
3. **Output-Ausnahme in jeder Stufe**: Alles, was `sherpa plan`/`apply` im Zielrepo erzeugt, gehört dem Nutzer ohne
   Auflagen (Muster: GCC Runtime Library Exception). Sonst fragt die Rechtsabteilung eines Kunden, ob ihr Harness
   „abgeleitetes Werk" ist.
4. **CLA oder DCO ab dem ersten externen Pull Request**, damit das Recht auf spätere Umlizenzierung erhalten bleibt.

## Alternativen
- Open Source (MIT/Apache) für maximale Reichweite: abgelehnt, nicht umkehrbar und ohne Zusatzprodukt kein Erlös.
- AGPL-Dual-Lizenz: abgelehnt, greift bei einem lokalen CLI nicht; Firmen zahlen nur aus Compliance-Angst.
- BUSL mit Change Date (Terraform-Erzählung „wird nach vier Jahren Apache"): offen; als Ergänzung zu PolyForm möglich,
  falls die Marketing-Wirkung den Erlösverzicht wert ist.

## Konsequenzen
- README: kein Lizenz-Badge, kein „open source"; ehrlich „source-available geplant". Die Regel „nur Badges für Dinge,
  die es gibt" gilt weiter.
- Abhängigkeiten müssen proprietäre Nutzung erlauben: aktuell keine Laufzeit-Abhängigkeit, PyYAML (geplant) ist MIT.
- Externe Beiträge sind bis zum CLA/DCO nicht annehmbar; solange Andrei alleine schreibt, ist nichts zu tun.
