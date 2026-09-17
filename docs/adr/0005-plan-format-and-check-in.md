# ADR-0005 — Plan file as YAML; plan and state are checked into the target repo, the model is not

**Status:** accepted · **Date:** 2026-09-16 · **Decision:** Andrei (format delegated to Claude)

## Context
`sherpa plan` produces a file a human **reads and edits** at approval time (`decision: accept | reject`).
`sherpa apply` writes a state that must tell the next run what Sherpa generated and what was hand-edited. Both
live in the target repo under `.sherpa/`.

## Decision
1. **`.sherpa/harness-plan.yaml`** — YAML, read and written with PyYAML (`safe_load`/`safe_dump`, fixed field
   order, fixed indentation). The first and, for now, only runtime dependency of Sherpa.
2. **`.sherpa/state.json`** — JSON (stdlib). Written by machines, only read by humans.
3. **Checked in** to the target repo: `harness-plan.yaml` and `state.json`. **Not** checked in:
   `codebase-model.json` (reproducible from the `origin/<trunk>` rev). `sherpa apply` creates
   `.sherpa/.gitignore` with `codebase-model.json` for that.

## Reasoning
- Approval is the moment the human touches the plan. YAML with a comment header and one-line evidence is readable
  for that; JSON without comments and with mandatory quoting is not.
- Plan and state are what a reviewer must see in the PR ("which harness parts are added, what was approved").
  Terraform practice: state without versioning leads to drift nobody sees.
- The model is large (a 15k-file monorepo yields 15k file entries) and byte-identical for the same rev — checking
  it in would only produce diff noise.
- Stdlib-first (ADR-0001) remains the principle; PyYAML is the one justified exception because the format is a
  product decision, not a convenience.

## Consequences
- `pyproject.toml`: `dependencies = ["pyyaml>=6"]`.
- Plan schema as JSON Schema (`src/sherpa/schemas/harness-plan.schema.json`); YAML is validated against it after
  loading — the format changes nothing about the check (since ADR-0042 with the stdlib validator on every install).
- Determinism: fixed field order (`kind` first, `reason` last), `allow_unicode=True`, `width=120` — two runs,
  same bytes (refined in ADR-0012: order instead of `sort_keys`).
