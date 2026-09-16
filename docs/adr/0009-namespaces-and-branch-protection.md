# ADR-0009 — Namespaces (product, package, org) and branch protection without rulesets

**Status:** accepted · **Date:** 2026-09-16 · **Code:** `pyproject.toml`, `.githooks/pre-push`, `README.md`

## Context
Creating the GitHub organisation showed that names live in separate namespaces: `github.com/sherpa` (org/user) is
taken, `sherpa` on PyPI has belonged to the Chandra/CIAO astrophysics package for years (`pip install sherpa`
installs that), repo names are unique per owner only, and the CLI command is registered nowhere. In addition,
GitHub rulesets and classic branch protection are not enforced on **private** repos in the Free plan — neither on
personal accounts nor in a Free org; that needs Pro (personal) or Team (org).

## Decision
1. **Product and CLI are called `sherpa`** — that is what the customer types and reads.
2. **The Python distribution is `sherpa-harness`** (`pyproject.toml` `name`); the import package stays `sherpa`.
   Same pattern as `beautifulsoup4` → `bs4`. `uv tool install sherpa-harness` is conflict-free on PyPI and in
   private indexes; the release workflow (M2b) uses this name.
3. **GitHub org `sherparc`**, repo `sherparc/Sherpa`; GitHub redirects old URLs, docs point to the new one.
4. **Branch protection locally instead of server-side**: `main` changes only through PR + squash merge. A
   versioned `pre-push` hook (`.githooks/pre-push`, enabled via `git config core.hooksPath .githooks`) refuses
   direct pushes to `main`/`master`. A ruleset `main` exists on GitHub (PR required, status checks, linear
   history, no force pushes, no deletion) and becomes effective automatically once the plan allows it.

## Alternatives
- Make the repo public (rulesets are free then): rejected, Sherpa is a product.
- GitHub Team/Pro right away: left open; the hook removes the urgency, the ruleset is prepared.
- Package name `sherpa-cli`: free, but says nothing about what it is; `sherpa-harness` describes the domain.

## Consequences
- The hook only protects clones where `core.hooksPath` is set (README "Development", CLAUDE.md); `--no-verify` is
  the deliberate escape hatch.
- Every step creates a branch `task/<topic>` and a PR; this matches the rule "show the diff before committing".
- Renaming product or org touches exactly three places: `pyproject.toml`, README links, CLAUDE.md.
