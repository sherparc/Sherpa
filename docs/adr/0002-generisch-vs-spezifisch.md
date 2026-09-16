# ADR-0002 — Trennung generisch (Template) vs. projektspezifisch (Adapter)

**Status:** vorgeschlagen · **Datum:** 2026-09-16

## Kontext
Das Referenz-Harness ist n = 1: ein Autor, ein Projekt, .NET, Outcome 15/15 `unknown`. Ein Template,
das daraus ohne Trennung abgeleitet wird, baut die Annahmen dieses einen Projekts unbemerkt in jedes Zielrepo ein.
Sherpa ist ein generisches Produkt; das Referenz-Projekt wird in Sherpa-Docs und -Code nicht beim Namen genannt.

## Entscheidung
Vor M3 wird jedes Element des Referenz-Harness einer von drei Klassen zugeordnet:

| Klasse | Beispiele | Landet in |
|---|---|---|
| **Generisch** | Owner-Prinzip, DERIVED VIEW, `MOVED:`, Struktur-/Owner-Regeln des Checkers, Hook-Schema, stop-gate, Outcome-Label, Plan-Konvention, Golden-Fragen-Format | `sherpa/templates/` |
| **Adapter** | Code-Anker-Regel, Test-Runner-Script, Modul-Layout `src/<Prefix>.*`, Trunk-Name | `sherpa/adapters/<lang>/` |
| **Projekt-only** | Obsidian-Projektion, die konkreten Librarian-Scopes, IDE-Bezüge | bleibt im Projekt |

## Konsequenzen
- Der Referenz-Checker wird nicht kopiert, sondern in generischen Kern + Adapter-Regeln zerlegt.
- Was in keine Klasse passt, wird als Frage in `docs/plan.md` §6 geführt — nicht still übernommen.
