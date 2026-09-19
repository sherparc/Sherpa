# ADR-0010 — Licensing in two stages: proprietary now, source-available at the public release

**Status:** accepted · **Date:** 2026-09-16 · **Code:** `LICENSE`, `pyproject.toml`, `README.md` ·
**Second stage taken by:** ADR-0051 (PolyForm Small Business or Noncommercial, 2026-09-19)

## Context
Sherpa is to be sold to companies later while gaining reach among developers. Without a `LICENSE` file "all
rights reserved" applies, but nobody knows it — and a licence change only works in one direction: as the sole
author Andrei can move from proprietary to open at any time; a version once published under MIT/Apache stays free
forever. So the decision must be made *before* the first public commit, not after.

The common models fit the goal "companies pay, individuals use for free" differently:

| Model | Example | Internal company use |
|---|---|---|
| MIT / Apache (open core) | most CLIs | free; revenue only from add-on products that do not exist yet |
| AGPL + commercial dual licence | MongoDB (formerly) | free — AGPL triggers on distribution/SaaS, not on a locally running CLI |
| BUSL 1.1 / FSL | Terraform, Sentry | free — only a competing product is forbidden |
| Elastic License 2.0 | Elasticsearch | free — only the managed service is forbidden |
| PolyForm Small Business 1.0.0 | — | free up to 100 people / USD 1M revenue, licence required above |
| PolyForm Noncommercial 1.0.0 | — | every commercial use needs a licence |

## Decision
1. **Now (repo private): proprietary `LICENSE`** — "all rights reserved", contact for commercial licences and
   evaluation. `pyproject.toml` carries `license = "LicenseRef-Proprietary"`, no `License ::` classifier.
2. **At the public release: PolyForm Small Business 1.0.0** (fallback: PolyForm Noncommercial if every company is
   to pay). Source-available, lawyer-drafted text, Docker Desktop / JetBrains model: small and private free, large
   companies buy. That will be its own ADR when the time comes.
3. **Output exception in every stage**: everything `sherpa plan`/`apply` generates in the target repo belongs to
   the user without obligations (pattern: GCC Runtime Library Exception). Otherwise a customer's legal department
   will ask whether their harness is a "derived work".
4. **CLA or DCO from the first external pull request**, so the right to relicense later is preserved.

## Alternatives
- Open source (MIT/Apache) for maximum reach: rejected, irreversible and without an add-on product no revenue.
- AGPL dual licensing: rejected, does not bite for a local CLI; companies would pay only out of compliance fear.
- BUSL with a change date (the Terraform story "becomes Apache after four years"): open; possible as a complement
  to PolyForm if the marketing effect is worth the revenue given up.

## Consequences
- README: no licence badge, no "open source"; honestly "source-available planned". The rule "badges only for
  things that exist" continues to apply.
- Dependencies must permit proprietary use: PyYAML is MIT.
- External contributions cannot be accepted until CLA/DCO exists; as long as Andrei writes alone, nothing to do.
