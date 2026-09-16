# ADR-0004 — Model providers: own thin layer, no LangChain/LangGraph

**Status:** accepted · **Date:** 2026-09-16

## Context
Sherpa must not be tied to one model vendor. Developers run local OpenAI-compatible servers (vLLM, Ollama) next to
cloud providers (Anthropic, OpenRouter, …). The question was whether LangChain or LangGraph should carry this
integration and the knowledge architect.

## Decision
Own provider interface (`sherpa/llm/`), ~150 lines, two protocols:

| Protocol | Covers | Structured output |
|---|---|---|
| OpenAI-compatible (`/v1/chat/completions`) | vLLM, Ollama, OpenRouter, Mistral, Gemini gateway, … | `response_format`/`guided_json` where available, else schema validation + retry |
| Anthropic native | Claude family | tool use with JSON Schema |

Shared contract: `complete(system, user, schema) -> dict`; output is **always** validated against the plan JSON
Schema; `model`/`prompt_hash` in the plan header. The provider is configuration, not code (`sherpa.toml [llm]`).

## Why no LangChain / LangGraph
- The architect is **one** structured call per plan (model in, plan out) — no chain, no graph.
- LangChain abstracts exactly the provider layer that is 150 lines here, and brings a large dependency net with
  frequent breaking changes. For a stdlib-first tool that is the wrong trade.
- LangGraph pays off for long-lived, branching agent runs with checkpoints. Sherpa demands determinism outside
  `plan` — a graph runtime with its own state contradicts the state model (`.sherpa/state.json`).
- Multi-step runs (e.g. propose → critique → revise), if ever needed, are an explicit Python loop with
  intermediate artefacts on disk — testable, diffable, no runtime.

## Flip criterion
Re-evaluate LangGraph when the architect needs ≥ 3 dependent LLM steps with resume after abort **and** the own
loop implementation exceeds 500 lines.
