# ADR-0026 — Change coupling leaves out the root module when other modules exist

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei

## Context

ADR-0021 measures temporal coupling between modules on commits below a size cap. A root manifest next to other
manifests makes the root module the catch-all: it owns every file no deeper manifest claims — docs, tests,
scripts, CI, the README. On such a repository in the corpus (16 modules, the root module holding 64 % of the
files) three of the four most active modules named the root module as their first partner with shares of
0.45–0.74, and the cap did not filter a single commit: the rows were true and said only "touches the rest".

## Decision

When more than one module exists, the root module (path `""`) is excluded from coupling: its files do not count
as a touched module, so it neither appears as a partner nor gets partners, and it does not count towards the
cap of a commit. The model records the excluded module id in `coupling.excluded` (`null` when nothing was
excluded). A lone root module (single-manifest repository) is not a catch-all and stays measured — its
sub-units are plan §6 Q13.

## Reasoning

- Tornhill couples logical units; "the rest of the repository" is not one. With code-maat the answer is to
  filter the log by pattern before the analysis; sherpa knows the bucket by construction and needs no
  configuration.
- Recording the exclusion keeps the number honest, as `skipped_commits` does for the cap.

## Consequences

- `compute_coupling(…, exclude=)`, wired in `scan.scan`; schema v4 gains the optional field `coupling.excluded`
  (older v4 models still load).
- Corpus check: partner rows 21 → 11 on the 16-module repository, 15 → 13 on the 122-module one (its root
  module holds 10 % of the files and had two rows), unchanged where no root manifest exists.
- Lost on purpose: coupling of a root module that is a real package (a Python service with a `web/` package
  beside it). When such a repository shows a pair worth knowing, ADR-0027's sub-units are the units to couple.
