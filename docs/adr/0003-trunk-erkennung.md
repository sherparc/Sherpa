# ADR-0003 — Scan immer gegen `origin/<trunk>`, Trunk-Erkennung in fester Reihenfolge

**Status:** akzeptiert · **Datum:** 2026-09-16 · **Code:** `src/sherpa/gitinfo.py`, Tests `tests/test_gitinfo.py`

## Kontext
Der lokale `HEAD` steht oft auf einem Task-Branch; Messungen dagegen sehen plausibel aus und sind falsch
(Trunk-Disziplin, Lehre aus der Harness-Analyse-Praxis). Sherpa bekommt nur einen Pfad und muss den Hauptbranch selbst finden.

## Entscheidung
1. Ohne Remote `origin` kein Scan (Fehler, kein Fallback auf lokale Branches).
2. `sherpa scan` ruft `git fetch origin` (abschaltbar mit `--no-fetch`), danach:
3. Trunk in dieser Reihenfolge:
   - `trunk:` aus `sherpa.yaml` (Override, mit oder ohne `origin/`-Präfix)
   - `refs/remotes/origin/HEAD` — von `git clone` gesetzt; fehlt es: `git remote set-head origin -a`
   - erster existierender Kandidat: `main`, `master`, `dev`, `develop`, `trunk`
4. Das Modell trägt `trunk.ref`, `trunk.source`, `trunk.rev`; alle Churn-Zahlen beziehen sich auf `trunk.rev`.

## Konsequenzen
- Reproduzierbar: gleicher `trunk.rev` → gleiches Modell, unabhängig vom ausgecheckten Branch (Test `test_local_head_is_ignored`).
- Ein Repo mit ungewöhnlichem Hauptbranch braucht eine Zeile Konfig statt einer Heuristik, die rät.
