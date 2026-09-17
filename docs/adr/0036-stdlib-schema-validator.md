# ADR-0036 — A stdlib validator for the shipped schemas: production checks what the tests check

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei · **Amends:** ADR-0005 (plan validation
"when `jsonschema` is installed")

## Context

The three index files have JSON schemas under `src/sherpa/schemas/`, but validation ran only when `jsonschema`
was importable — a dev extra, absent from every wheel install. An external review of v0.7.1 reproduced the
consequence without the extra: `plan_from_dict` accepted `schema_version: 999`, `kind: wizard` and
`decision: rejcet`, and `selected()` — which tests `decision != "reject"` — rendered the agent the human had
tried to refuse. `plan` caught decision typos in `decisions_of`, but `apply`, `status` and `adopt` read the plan
through `plan_from_dict` and did not. The state and the model guard their `schema_version` by hand; the plan,
the one file a human edits, guarded nothing. The test suite, always with the extra, never saw it.

## Decision

1. `sherpa/schema.py` (stdlib, ~60 lines) validates a document against a shipped schema. It interprets the
   keyword subset the three schemas use — `type`, `enum`, `const`, `required`, `properties`,
   `additionalProperties`, `items`, `pattern`, `minimum`, `maximum` — and raises `SchemaError(path, message)`
   at the first violation, with messages shaped like jsonschema's (`'rejcet' is not one of ['accept', 'reject',
   None]`, `1 was expected`). `format` stays descriptive, as in jsonschema's default validator.
2. `yamlio.validate`, `state.validate` and `model.validate` use it unconditionally; the messages keep their
   prefixes (`harness-plan.yaml invalid at entries/0/decision: …`).
3. `jsonschema` stays a dev extra and becomes the reference: `tests/test_schema.py` runs one input matrix — the
   real plan, state and model of a fixture plus broken variants — through both validators and asserts that they
   accept and reject the same documents at the same path. A CLI test hides `jsonschema` from `sys.modules` and
   walks `apply`, `status` and `adopt` with `decision: rejcet`, `schema_version: 999` and `kind: wizard`.
4. A schema may use a new keyword only together with the validator and the matrix.

## Reasoning

- Stdlib-first (plan §2) rules out a runtime dependency for a 60-line need; Renovate ships its own validator
  for the same reason — the config file is the product's interface and must be checked wherever the product
  runs, not only where its developers run it.
- Duplicating the enums in Python next to the schema was the alternative; two owners for one fact drift. Reading
  the schema the tests read keeps one owner (owner principle) and the matrix keeps the two validators honest.
- First-violation reporting is what pip, Terraform and Git do for a bad file: one line, the path, the fix.

## Consequences

- `sherpa.schema.load(name)` caches the parsed schema; `SchemaError.path` is the JSON-pointer-like location.
- `decisions_of` keeps its own decision check for the `plan` merge path (it names kind and target); the schema
  now catches the same typo one layer below, on every reader.
- `state.load` and `model.load` still trust their own writers and check only `schema_version` in `from_dict`;
  the full validation runs where it always did (after `scan`, in the tests) — those files are sherpa's, not
  the user's, and `adopt` rebuilds a torn state (ADR-0017).
