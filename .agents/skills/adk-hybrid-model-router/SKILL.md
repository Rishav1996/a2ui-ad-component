---
name: adk-hybrid-model-router
description: Manages Google ADK model instantiation across local Ollama (LiteLlm) and Google AI Studio Gemini Free Tier, handling rate limits, token tracking, and environment configuration.
---

# ADK Hybrid Model Router

## Overview
This skill governs how models are selected and instantiated within Google Agent Development Kit (`google-adk`). It ensures seamless switching between local open-source models running via Ollama and Google AI Studio's Gemini Free Tier.

## Core Rules & Guardrails

1. **Google AI Studio Free Tier Authentication:**
   - Always ensure `GOOGLE_GENAI_USE_VERTEXAI=FALSE` when using API keys from Google AI Studio (`GOOGLE_API_KEY`).
   - Using Vertex AI auth with an AI Studio key results in 401/403 authorization failures.
   - Default Gemini models: `gemini-2.5-flash` or `gemini-2.5-flash-lite`.

2. **Ollama Integration via LiteLlm:**
   - Always instantiate Ollama models through `LiteLlm(model="ollama_chat/<tag>")` (e.g., `ollama_chat/qwen2.5-coder:7b`).
   - **CRITICAL:** Never use the raw `ollama/<tag>` prefix. The `ollama/` prefix invokes the completion endpoint rather than the chat completion endpoint, breaking multi-turn chat formatting and system instructions in ADK agents.
   - Configure `OLLAMA_API_BASE` (default: `http://localhost:11434`) via environment variables.

3. **Execution Modes:**
   - `ollama`: All agents (SUT and evaluators) use local Ollama models.
   - `gemini`: All agents use Gemini API.
   - `hybrid`: System Under Test (SUT) agents run locally on Ollama (e.g. `qwen2.5-coder:7b`), while Judges and Evaluators run on Gemini Free Tier (`gemini-2.5-flash`).

4. **Token Usage Tracking:**
   - Extract `usage_metadata` from `llm_response.usage_metadata` (`prompt_token_count`, `candidates_token_count`, `total_token_count`) to track overhead between prompt-injected vs callback-injected architectures.

5. **Rate-Limit Throttling:**
   - For batch evaluation or loop testing with Gemini Free Tier, introduce retry backoff and rate pacing to respect the 15 RPM / 1M TPM free quota.

