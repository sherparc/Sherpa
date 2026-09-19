# ADR-0051 — Public release: PolyForm Small Business 1.0.0 or PolyForm Noncommercial 1.0.0, at the user's option

**Status:** accepted · **Date:** 2026-09-19 · **Decision:** Andrei (the launch question of plan §9.1) ·
**Takes:** the second stage of ADR-0010 · **Code:** `LICENSE`, `pyproject.toml`, `README.md`

## Context
ADR-0010 decided licensing in two stages: proprietary while the repository is private, a source-available
licence "at the public release", to be its own ADR when the time comes. The time came sideways: the repository
has been public on GitHub since it was created (2026-09-16), and the product reached the point where the
remaining gaps are launch gaps, not code gaps (plan §9.1: "Sherpa has 0 stars and a private wheel"). Whoever
finds the repository today reads a `LICENSE` that grants nothing — `uv tool install git+https://…` from the
README is, strictly, not permitted. That contradiction has to close before anyone is pointed at the repository.

The licence text itself settles what ADR-0010 left as a fallback. PolyForm Small Business 1.0.0 has exactly one
permitted purpose, "use of the software for the benefit of your company" under the 100-people / USD 1M limits;
its author confirmed in [polyform-licenses#58](https://github.com/polyformproject/polyform-licenses/issues/58)
that no other section adds a purpose, so a hobby project or a personal experiment by someone who works for a
large company is not covered — and his answer is the standard remedy: "licensors can choose to offer code under
both PolyForm Noncommercial and PolyForm Small Business", which adds the small-business permission on top of the
noncommercial one. PolyForm Noncommercial 1.0.0 names personal uses (study, hobby projects, experiments) and
noncommercial organisations (charities, universities, public institutions) as permitted purposes.

## Decision
1. **Sherpa is licensed under PolyForm Small Business 1.0.0 or PolyForm Noncommercial 1.0.0, at the user's
   option** — SPDX `PolyForm-Small-Business-1.0.0 OR PolyForm-Noncommercial-1.0.0`. `LICENSE` carries both texts
   verbatim, the `Required Notice:` line and the output exception; `pyproject.toml` carries the expression, and
   the wheel built from the next tag ships it in its metadata.
2. **Who is free, who pays.** Free: any individual for personal use, any noncommercial organisation, and any
   company under the Small Business limits (fewer than 100 employees and contractors, under USD 1M revenue in the
   prior tax year, inflation-adjusted per the licence). A company above those limits needs a commercial licence
   — the contact stays in `LICENSE`.
3. **The output exception stays in every stage** (ADR-0010 §3): everything `sherpa plan` and `sherpa apply`
   write into the user's repository belongs to the user without obligations. It is stated as an additional
   permission next to the licence texts, which are used unchanged.
4. **Contributions need a DCO sign-off** (ADR-0010 §4) from the first external pull request; the `CONTRIBUTING.md`
   that says so is part of the launch slice (M2c), not of this ADR.
5. **No version bump for the licence alone.** The next tag ships under the new licence; the release before it
   (v0.7.9) keeps the proprietary metadata it was built with — a wheel is never rewritten (ADR-0018).

## Alternatives
- **Small Business alone** (ADR-0010's first choice): rejected on the licence author's reading — it would leave
  the very people a launch addresses, individual developers trying the tool on a side project, unlicensed.
- **Noncommercial alone** (ADR-0010's fallback): rejected — every company, however small, would need a written
  licence before `sherpa doctor`; the Docker Desktop / JetBrains pattern that ADR-0010 chose lives from small
  teams that use the tool free and grow into the paid tier.
- **BUSL 1.1 with a change date** (Terraform, Sentry): still open as a complement — it forbids only a competing
  product and converts to Apache after a fixed period. Not taken now: the two PolyForm texts are shorter, say
  who is free in one sentence, and keep the relicensing option that BUSL's change date would give away on a date.
- **MIT / Apache**: rejected in ADR-0010, unchanged — irreversible, and without an add-on product no revenue.

## Consequences
- README `## License` says it in two sentences and links `LICENSE`; no licence badge until PyPI shows the
  classifier for real (the rule "badges only for things that exist").
- Docs that explained the token by "the repository is private" (`getting-started`, `self-update`, `doctor`,
  the environment table, `release.yml`) say what is true instead: the Releases API is read with a token when one
  is there, the tag through `git ls-remote` without one — `update.py` keeps that order until M2c switches the
  index to PyPI (ADR-0018 §5).
- ADR-0018 §5 becomes due: `release.yml` gains a PyPI publish step, `self-update` reads the index. The name
  `sherpa-harness` is free on PyPI (checked 2026-09-19); that is the first item of M2c.
- A contributor's pull request is not merged before `CONTRIBUTING.md` with the DCO exists (M2c).
- Flip criterion for the licence: the paid tier does not exist within a year of the launch, or the licence is
  the stated reason the second corpus-sized user declines — then BUSL with a change date, never MIT.
