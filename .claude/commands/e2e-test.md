---
description: End-to-end test of the sherpa CLI on the local corpus repository ($SHERPA_E2E_REPO or the argument) — every claim of README, CLAUDE.md and the ADR index as a thesis with a pass criterion; report in the chat, corpus left as found.
---

Run the skill `.claude/skills/e2e-test/SKILL.md` as the agent `.claude/agents/e2e-tester.md` on the corpus
repository `$ARGUMENTS` (empty = `$SHERPA_E2E_REPO`). Every thesis, in order; nothing written into this
repository; the corpus is cleaned at the end and the empty `git status --short --ignored` is part of the
report. Findings go into the chat in the five-section shape the agent defines, in neutral terms — the corpus
is never named.
