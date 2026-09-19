# ADR-0054 — The PyPI package is `sherparc`: one word, the org's name

**Status:** accepted · **Date:** 2026-09-19 · **Decision:** Andrei · **Amends:** ADR-0009 (package name),
ADR-0053 (the index's project) · **Code:** `pyproject.toml`, `src/sherpa/update.py`, `.github/workflows/release.yml`

## Context
ADR-0009 named the package `sherpa-harness` because `sherpa` on PyPI belongs to the Chandra modelling package
(still maintained, 4.18 in 2026) and PyPI names are global; the CLI and the import package stay `sherpa`. The
name went live on the index with v0.8.0 (ADR-0053) and read too long in the one line the README leads with:
`uv tool install sherpa-harness`. The install line is the first thing a reader types; the org's name is one word,
free on PyPI (checked 2026-09-19), and already what the repository URL says.

## Decision
1. **The PyPI project is `sherparc`.** `pyproject.toml` `name`, `update.PYPI_PROJECT`, the index check in
   `release.yml` and every install line follow; the wheel is `sherparc-<version>-py3-none-any.whl`. CLI,
   import package and the `.sherpa/` directory stay `sherpa` — nothing a user types after the install changes.
2. **`sherpa-harness` 0.8.0 stays on PyPI as it is** — not deleted, not shimmed. It was published on 2026-09-19
   at 07:50 UTC and replaced within the hour; a copy installed from it reads the old project's index and would
   report itself current, so the README and the release notes of v0.8.1 say `uv tool install sherparc` once.
   No alias package: a second project to keep in step for an hour-old release is not worth its maintenance.
3. **Trusted publishing stays as ADR-0053 set it** — the pending publisher for `sherparc` is registered with the
   same repository, workflow and environment; `release.yml` does not change beyond the project name.
4. **The module name of Sherpa's own harness follows the manifest** — the scanner names the root unit after
   `pyproject.toml`, so after this merge `sherpa plan .` on `main` renames the unit `sherpa-harness` → `sherparc`
   and `apply` moves the owner doc, the librarian skill and the kept `[reject]` decision with it. That is the
   normal path of a renamed unit (ADR-0048), not a special case.

## Alternatives
- **Keep `sherpa-harness`**: rejected by the reader's first line — the product's name is `sherpa`, the suffix
  explains nothing a reader does not already know from the sentence above it.
- **`sherpa-cli`**: free, shorter, but generic; says "a CLI" where `sherparc` says whose.
- **A PEP 541 request for `sherpa`**: not applicable — the holder is an active project.

## Consequences
- Version 0.8.1; the v0.8.1 release notes name the rename in one line.
- `CLAUDE.md`'s namespace rule reads: product, CLI and import package `sherpa`; PyPI package and org `sherparc`.
- The pending publisher `sherpa-harness` on pypi.org can be removed; the project page of `sherpa-harness` 0.8.0
  keeps its description, which points at the repository.
