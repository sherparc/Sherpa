# ADR-0043 — The CI matrix follows the event: Linux per pull request, Windows on `main`, macOS weekly

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei

## Context

The repository is private, and GitHub bills its minutes by runner: Linux 1×, Windows 2×, macOS 10×. `ci.yml` ran
Linux and Windows for two Python versions on every push to a pull request and on `main`; Windows takes 5–8× the
Linux wall time on this suite (plan §10.1) and so dominated the bill, and macOS was a comment in the matrix that
somebody had to remember to uncomment. Docs-only commits ran the whole matrix, a second push cancelled nothing,
and a hung job had six hours to spend.

## Decision

1. The matrix is chosen by the event: pull request → Linux; push to `main` → Linux + Windows; `schedule`
   (Monday 06:00 UTC, on `main`) → macOS; `workflow_dispatch` → all three. Python 3.12 and 3.13 throughout.
2. `paths-ignore` for `**.md`, `docs/**`, `kb-sherpa/**`, `.claude/**`, `.githooks/**`, `LICENSE` on push and
   pull request — none of it is read by the tests.
3. `concurrency` per workflow and ref with `cancel-in-progress` — a newer push to the same branch cancels the
   older run.
4. `timeout-minutes`: tests 20, lint 5, release 15. pip is cached by `setup-python` everywhere, lint and release
   included.

## Reasoning

- The pull request is where commits arrive in bursts and where the fast signal matters; Windows on `main` still
  catches every merge before a tag, and a large path/encoding change gets its full matrix on request instead of
  by editing the workflow.
- macOS weekly on `main` keeps the arm64 laptop path honest at one tenth of the former exposure and with no
  human in the loop.
- No branch protection on the free plan, so a docs-only pull request without a CI run blocks nothing; the
  `.githooks/pre-push` guard covers `main`.

## Consequences

- `ci.yml` header documents the rule; CLAUDE.md, README and plan §5 name it. The manual run is
  `gh workflow run ci.yml --ref <branch>`.
- A Windows-only regression on a pull request surfaces on `main` after the merge — the fix is a follow-up PR;
  for changes to `gitinfo`, paths or encodings the manual run before the merge is the rule (CLAUDE.md).
- Not built: a lint job on the schedule (ruff has no OS dimension); Windows on a label — a manual run is enough.
