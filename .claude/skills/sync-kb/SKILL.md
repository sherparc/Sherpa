---
name: sync-kb
description: "Keep the Obsidian vault kb-sherpa/ (an ignored one-way projection of README, CLAUDE.md, docs/, the harness and the schemas) in sync with the repository; use after any doc change, or when a note in the vault looks stale."
---

# sync-kb — the vault is a projection, never a source

## Use when

- a doc, ADR, README, CLAUDE.md, agent, skill or schema changed
- `python3 scripts/sync-kb.py --check` reports notes out of date or stale
- someone edited a note inside `kb-sherpa/` — the edit is lost on the next sync; move it to the source file first

## Procedure

1. `python3 scripts/sync-kb.py --check` — lists notes that would change or vanish.
2. Edit the **source** files in the repository, never the vault.
3. `python3 scripts/sync-kb.py` — full mirror: front matter injected (`title`, `type`, `source`, `synced`,
   `tags`), stale notes removed, `Home.md` regenerated.
4. Open `kb-sherpa/Home.md` in Obsidian to browse; the layout mirrors repository paths so links resolve.

## Don't

- commit `kb-sherpa/` — it is in `.gitignore` on purpose; it is personal and regenerated.
- add sources to the vault by hand — extend `SOURCES` in `scripts/sync-kb.py`.
