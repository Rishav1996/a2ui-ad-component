# Rule: Zero Dummy Data & Mandatory True Agent Execution

## 1. Absolute Prohibition of Canned & Dummy Text
- NEVER write, return, or fall back to hardcoded template strings, canned "synthesized search summary" boilerplate, or generic architectural buzzwords (e.g., "Evaluated core system parameters", "Identified latency, throughput, and operational trade-offs").
- If an external tool (such as DuckDuckGo or web search) experiences a network timeout or failure:
  - Do NOT emit fake summaries.
  - The agent MUST utilize its own LLM reasoning (Gemini) to provide an authentic, intelligent, domain-appropriate answer to the user's query, or transparently disclose the tool search state.

## 2. Mandatory True Agent Execution
- All backend APIs, endpoints, and UI bridges MUST directly invoke the Google ADK Agent pipeline (using ADK `Runner` or agent execution).
- NEVER build "mock endpoints" or bypass the agent by hardcoding tool calls or fake agent steps in API route handlers. The LLM must always participate in query reasoning, intent classification, and response formatting.

## 3. Dynamic Commercial Data Only
- Sponsored recommendations and ads must be fetched dynamically from real ad search providers (SerpApi Google Shopping / Ads) or verified commercial partners.
- Zero placeholder URLs (`example.com`) or fake retail items are permitted anywhere in production code.

