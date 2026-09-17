# ADR-0020 — Sub-units for single-manifest repositories: a depth rule, overridable in `sherpa.toml`

**Status:** accepted · **Date:** 2026-09-17 · **Decision:** Andrei (§6 Q11) · **Implementation:** M3d

## Context
`units_of` takes modules from manifests and adds depth-1 directory units only when no root module exists. A
repository with one `pyproject.toml` or `package.json` at the root — the most common shape — is therefore one
unit, and the plan's strongest case (units, ranks, reasoned no's) never appears there (`docs/plan.md` §7.1 G2).
Sherpa itself is the example: `scan`, `plan`, `apply` are its subsystems; the plan says `1 owner-doc`. The
alternatives were a rule only, an explicit unit list in `sherpa.toml` only, or the rule with the list as the
override.

## Decision
1. **The rule.** When the root module is the only module, sub-units come from the first depth below the source
   root at which at least two directories meet `owner_doc_min_files` (ADR-0014). Python: packages
   (`__init__.py`); other ecosystems: directories. Test directories are excluded; the root module keeps the
   repository-level owner doc. Sub-units get ids `<module>/<dir>` and the module's ecosystem.
2. **The override.** `[plan] units = ["src/sherpa/*", "tools/cli"]` in `sherpa.toml` replaces the rule's result
   for that repository: globs relative to the root, resolved against directories, each match a unit. An empty
   list switches sub-units off. The console note names the key when the rule found sub-units, so the reader
   knows where to correct it.

## Reasoning
- A rule gives every repository the units on day 0 with zero configuration — the product promise is "run it,
  read the plan". A list only would move the first insight behind a config step.
- The rule will be wrong for some layouts (a `src/` with one package and a flat `lib/`); the override is the
  Terraform-style escape hatch: explicit beats inferred, and it is visible in the repository.
- Depth-first with a two-directory minimum avoids the degenerate case of one nested package becoming a "unit"
  identical to its parent.

## Consequences
- M3d implements the rule in `plan/rules.py` (`units_of`) and the key in `config.PlanConfig`; the plan for
  Sherpa's own repository then lists `scan`, `plan`, `apply` as units (acceptance in the milestone table).
- The configuration reference and `docs/concepts/harness-plan.md` document the rule and the key; goldens for a
  single-manifest fixture are added on purpose.
