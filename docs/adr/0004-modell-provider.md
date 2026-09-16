# ADR-0004 — Modell-Provider: eigene dünne Schicht, kein LangChain/LangGraph

**Status:** akzeptiert · **Datum:** 2026-09-16

## Kontext
Sherpa soll nicht nur mit Anthropic-Modellen arbeiten. Auf dem Zielsystem läuft vLLM lokal
(OpenAI-kompatibel, `http://localhost:8000/v1`, `qwen3.8-flash-next`); für Cloud kommen Anthropic, OpenRouter u. a.
in Frage. Die Frage war, ob LangChain oder LangGraph diese Anbindung und den Wissensarchitekten tragen sollen.

## Entscheidung
Eigene Provider-Schnittstelle (`sherpa/llm/`), ~150 Zeilen, zwei Protokolle:

| Protokoll | Deckt ab | Structured Output |
|---|---|---|
| OpenAI-kompatibel (`/v1/chat/completions`) | vLLM, Ollama, OpenRouter, Mistral, Gemini-Gateway, … | `response_format`/`guided_json` wo vorhanden, sonst Schema-Validierung + Retry |
| Anthropic nativ | Claude-Familie | Tool-Use mit JSON-Schema |

Gemeinsamer Vertrag: `complete(system, user, schema) -> dict`, Output **immer** gegen das Plan-JSON-Schema validiert,
`model`/`prompt_hash` im Plan-Header. Provider ist Konfig, kein Code (`sherpa.yaml: llm:`).

## Warum kein LangChain / LangGraph
- Der Architekt ist **ein** strukturierter Aufruf pro Plan (Modell rein, Plan raus) — keine Kette, kein Graph.
- LangChain abstrahiert genau die Provider-Schicht, die hier 150 Zeilen ist, und bringt dafür ein grosses
  Abhängigkeitsnetz mit häufigen Breaking Changes. Für ein stdlib-first-Tool ist das die falsche Bilanz.
- LangGraph lohnt sich bei langlebigen, verzweigten Agent-Läufen mit Checkpoints. Sherpa fordert Determinismus
  ausserhalb von `plan` — eine Graph-Runtime mit eigenem State widerspricht dem State-Modell (`sherpa-state.json`).
- Mehrstufige Läufe (z. B. propose → critique → revise) sind, falls nötig, ein expliziter Python-Loop mit
  Zwischenartefakten auf Platte — testbar, diffbar, ohne Runtime.

## Kippkriterium
LangGraph erneut prüfen, wenn der Architekt ≥ 3 abhängige LLM-Schritte mit Wiederaufnahme nach Abbruch braucht
**und** die eigene Loop-Implementierung > 500 Zeilen wird.
