# ADR-0001 — Implementation language: Python

**Status:** accepted · **Date:** 2026-09-16

## Context
Sherpa has three stages: scanner (deterministic), knowledge architect (LLM), applier (deterministic). Rust and
Python were the candidates. The development machine (Linux ARM64) has Python 3.12 and no Rust toolchain.

## Decision
Python 3.12, stdlib-first, `src/` layout, `sherpa` as the entry point.

## Reasoning
- The artefacts Sherpa generates are Python: harness checkers, hooks, outcome scripts, librarian scripts. Sherpa
  must produce these templates **and** execute them — one language, one test run.
- The middle stage (LLM) is native in Python (Anthropic SDK; Claude Code hooks are Python scripts).
- The scanner is not compute-bound: `git log`, project files; tree-sitter has Python bindings. The bottleneck is
  git I/O, not the language.
- One author, high iteration speed. Correctness comes from self-tests of the generated checkers, not from the
  type system — that stays.

## What Rust would have brought
- A static binary for distribution (no venv).
- Compile-time guarantees for the model/plan/state schemas.
- A faster scanner on very large monorepos.

## Flip criterion
A Rust scanner (via PyO3, not a rewrite) if `sherpa scan` takes > 60 s on a target repo **or** distribution to
third parties without a Python environment becomes a requirement. Schemas are kept as JSON Schema from M1 so a
later Rust core can adopt them without redefinition.
