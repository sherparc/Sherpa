# ADR-0009 — Namensräume (Produkt, Paket, Org) und Branch-Schutz ohne Rulesets

**Status:** akzeptiert · **Datum:** 2026-09-16 · **Code:** `pyproject.toml`, `.githooks/pre-push`, `README.md`

## Kontext
Beim Anlegen der GitHub-Organisation stellte sich heraus, dass Namen in getrennten Namensräumen leben:
`github.com/sherpa` (Org/User) ist vergeben, `sherpa` auf PyPI gehört seit Jahren dem Chandra/CIAO-Astrophysik-Paket
(`pip install sherpa` installiert das), Repo-Namen sind nur je Owner eindeutig, und der CLI-Befehl ist nirgends registriert.
Ausserdem greifen GitHub-Rulesets und klassische Branch Protection auf **privaten** Repos im Free-Plan nicht — weder auf
persönlichen Accounts noch in einer Free-Org; dafür braucht es Pro (persönlich) oder Team (Org).

## Entscheidung
1. **Produkt und CLI heissen `sherpa`** — das ist, was der Kunde tippt und liest.
2. **Python-Distribution heisst `sherpa-harness`** (`pyproject.toml` `name`), Import-Paket bleibt `sherpa`.
   Gleiches Muster wie `beautifulsoup4` → `bs4`. Damit ist `uv tool install sherpa-harness` auf PyPI und in privaten
   Indizes konfliktfrei; Release-Workflow (M2b) benutzt diesen Namen.
3. **GitHub-Org `sherparc`**, Repo `sherparc/Sherpa`; alte URLs werden von GitHub umgeleitet, Doku zeigt auf die neue.
4. **Branch-Schutz lokal statt serverseitig**: `main` wird nur über PR + Squash-Merge verändert. Ein versionierter
   `pre-push`-Hook (`.githooks/pre-push`, aktiv über `git config core.hooksPath .githooks`) verweigert direkte Pushes
   nach `main`/`master`. Ein Ruleset `main` ist in GitHub angelegt (PR-Pflicht, Status-Checks, lineare Historie,
   keine Force-Pushes, kein Löschen) und greift automatisch, sobald der Plan es erlaubt.

## Alternativen
- Repo public machen (Rulesets greifen kostenlos): abgelehnt, Sherpa ist ein Produkt.
- GitHub Team/Pro sofort: offen gelassen; der Hook macht es nicht dringend, das Ruleset ist vorbereitet.
- Paketname `sherpa-cli`: frei, sagt aber nicht, was es ist; `sherpa-harness` beschreibt die Domäne.

## Konsequenzen
- Der Hook schützt nur Clones, in denen `core.hooksPath` gesetzt ist (README „Entwicklung", CLAUDE.md); `--no-verify`
  ist der bewusste Notausgang.
- Jeder Schritt erzeugt einen Branch `task/<thema>` und einen PR; das passt zur Regel „Diff vor Commit zeigen".
- Bei Umbenennung von Produkt oder Org sind genau drei Stellen betroffen: `pyproject.toml`, README-Links, CLAUDE.md.
