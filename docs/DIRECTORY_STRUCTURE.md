# Codebase Directory Structure & Developer Navigation Guide

Welcome to the **A2UI v0.9 Ad Component & Google ADK Multi-Agent Engine** repository. This guide provides an architectural map of the project to help developers, researchers, and open-source contributors understand the layout in under two minutes.

---

## 1. High-Level Directory Tree

```
a2ui-ad-component/
├── .agents/                           # Agentic skills & guardrail rules
│   ├── rules/                         # No-dummy-data and security rules
│   └── skills/                        # ADK custom skill definitions
│       ├── a2ui-v09-catalog-builder/  # Rules for authoring A2UI v0.9 JSON catalogs
│       ├── adk-a2ui-callback-injector/# Rules for deterministic ADK hook injection
│       ├── adk-hybrid-model-router/   # Multi-provider routing (Gemini & Ollama)
│       └── adk-multiagent-benchmarker/# Benchmark pipeline orchestration
│
├── catalogs/                          # Canonical A2UI v0.9 Component Specifications
│   ├── ad_catalog.json                # JSON Schema for AdBanner & SponsoredCard
│   ├── common_types.json              # Canonical common types ($defs)
│   └── examples/                      # Valid v0.9 createSurface example payloads
│       └── sponsored_card.json        # Few-shot surface example
│
├── docs/                              # Technical Documentation & Research Publications
│   ├── ARCHITECTURE.md                # System design, RTB auction & multi-turn streaming
│   ├── DIRECTORY_STRUCTURE.md         # This developer navigation map
│   └── medium_article.md              # In-depth technical publication article
│
├── renderers/                         # Client-Side UI Renderers (A2UI Client)
│   ├── lit/                           # Web Component implementations (TypeScript)
│   │   ├── ad-banner.ts               # <a2ui-ad-banner> component with locked badge
│   │   └── sponsored-card.ts          # <a2ui-sponsored-card> 3-card search renderer
│   └── preview.html                   # Standalone browser visual previewer
│
├── google_a2a_agent/                  # Core Python Agent & Auction Engine
│   ├── agents/                        # Multi-Agent Pipeline Definitions
│   │   ├── coordinator.py             # Root SequentialAgent & search_and_ad_coordinator
│   │   ├── eval_agents.py             # Benchmark judges & behavioral auditors
│   │   └── sut_agents.py              # Mode A (Prompt) & Mode B (Callback) SUT agents
│   ├── auction/                       # Ad Exchange, Vickrey Auction & Callbacks
│   │   ├── ad_client.py               # Live SerpApi Google Shopping & DSP client
│   │   ├── ad_sandbox.py              # SQLite Vickrey auction ledger & click telemetry
│   │   └── callbacks.py               # ADK lifecycle callback hooks & security auditor
│   ├── governance/                    # Capacity, Quota & Model Routing
│   │   ├── quota_manager.py           # Live SerpApi & Gemini LLM quota tracking
│   │   └── model_router.py            # LiteLLM & Gemini model provider router
│   ├── schemas/                       # Schema Validation & Visual Rendering
│   │   ├── schema_manager.py          # A2uiSchemaManager (Draft 2020-12 validator)
│   │   └── visual_renderer.py         # Markdown and surface visual generator
│   ├── tools/                         # Executable ADK Tools
│   │   └── ad_tools.py                # simulate_ad_banner_click, search_knowledge_tool
│   ├── runner.py                      # Singleton ADK InMemoryRunner & SSE stream generator
│   └── __init__.py                    # Public API exports (100% backward-compatible)
│
├── tests/                             # Comprehensive Pytest Suite (31 unit tests)
│   ├── conftest.py                    # Pytest fixtures & environment setup
│   ├── test_ad_sandbox.py             # Auction logic, impression logging, and clicks
│   ├── test_api_endpoints.py          # FastAPI endpoint integration tests
│   ├── test_callbacks.py              # Hook mutation, 3-card injection, sanitization
│   ├── test_catalogs.py               # JSON schema validation & defect tests
│   ├── test_intent_and_ad_client.py   # Intent classification & SerpApi parsing
│   ├── test_model_router.py           # Provider routing & VertexAI flags
│   ├── test_multiagent_pipeline.py    # Multi-agent graph & callback tests
│   └── test_search_ad_cards.py        # Top-3 Vickrey auction & copy personalization
│
├── web_app/                           # Full-Stack Web Interface & API Server
│   ├── server.py                      # FastAPI server (SSE streaming & analytics endpoints)
│   └── static/                        # Frontend UI (HTML, CSS, Vanilla JS)
│       ├── index.html                 # Chat workspace & stream log dashboard
│       ├── styles.css                 # Glassmorphic CSS design system
│       └── app.js                     # Real-time SSE streaming & quota meters
│
├── Dockerfile                         # Production containerization
├── pyproject.toml                     # Python dependencies & build metadata
├── run_adk_server.py                  # Standalone FastAPI server launcher
├── LICENSE                            # Apache 2.0 Open-Source License
├── CITATION.cff                       # Citation File Format (CFF 1.2.0)
├── .zenodo.json                       # Zenodo archival configuration
└── README.md                          # Comprehensive project documentation
```

---

## 2. Component Directory Guide

### A. Core Agent Engine (`google_a2a_agent/`)
This is the heart of the backend. It implements the Google ADK multi-agent pipeline and the ad auction engine:

- **`google_a2a_agent/auction/`**:
  - `ad_client.py`: Connects to SerpApi to retrieve live Google Shopping and search ads. Falls back gracefully to local DSP mock campaigns if SerpApi is unconfigured or exhausted.
  - `ad_sandbox.py`: Manages the local SQLite ledger (`query_ad_audit` table) and computes the second-price Vickrey clearing price ($P_1 = \text{Bid}_2 + \text{₹1.00}$).
  - `callbacks.py`: Contains the `after_model_callback` hook that intercepts the agent output and injects verified sponsored cards into the A2UI surface.
- **`google_a2a_agent/agents/`**:
  - `coordinator.py`: Connects the `organic_search_agent` and `contextual_ad_agent` into a unified `SequentialAgent`.
  - `eval_agents.py`: Evaluator agents (`SchemaAuditor`, `BehavioralJudge`, `ActionLoopTester`) for benchmarking.
  - `sut_agents.py`: Defines the System-Under-Test agents (Mode A vs Mode B).
- **`google_a2a_agent/governance/`**:
  - `quota_manager.py`: Monitors Google Gemini Free Tier daily limits (1,500 RPD) and SerpApi monthly allowances (250/mo), triggering automated server-down protection if quotas are reached.
  - `model_router.py`: Handles model initialization across Google AI Studio and local Ollama (`LiteLlm`).
- **`google_a2a_agent/schemas/`**:
  - `schema_manager.py`: Validates payloads against official A2UI Draft 2020-12 schemas offline.
  - `visual_renderer.py`: Generates the A2UI surface adjacency list and Markdown cards.
- **`google_a2a_agent/runner.py`**:
  - Provides `stream_search_pipeline_async` yielding Server-Sent Events (SSE) for sub-400ms streaming responses.

---

### B. Catalogs & Specifications (`catalogs/`)
Houses the declarative JSON schemas adhering strictly to the **A2UI v0.9 specification**:
- `ad_catalog.json`: Declares the component schemas for `AdBanner` and `SponsoredCard`, including required properties (`sponsor_name`, `target_url`, `headline`, `disclosure`).
- `common_types.json`: Canonical shared types like `Action`, `Border`, and color specifications.
- `examples/`: Full sample payloads demonstrating valid `createSurface` calls.

---

### C. Client-Side Renderers (`renderers/`)
Provides reference implementations for client applications displaying A2UI components:
- `renderers/lit/`: Lit / Web Component classes (`<a2ui-ad-banner>`, `<a2ui-sponsored-card>`) featuring locked "Sponsored" disclosure badges and secure external link handling (`rel="noopener noreferrer sponsored"`).
- `renderers/preview.html`: An interactive HTML previewer to test rendering components outside of the agent loop.

---

### D. Interactive Web App (`web_app/`)
The production web interface:
- `server.py`: FastAPI backend hosting SSE streaming (`GET /api/chat/stream`), analytics log (`GET /api/analytics`), click tracking (`POST /api/click`), and static file delivery.
- `static/index.html`: Responsive dual-view UI:
  1. **Continuous AI Chat**: Multi-turn chat workspace with live streaming text deltas and verified sponsor cards.
  2. **Search & Ad Stream Log**: Real-time query audit table with live quota progress meters.
- `static/app.js`: Client-side logic for SSE stream parsing, Markdown rendering, and quota UI binding.

---

## 3. Developer Extension Recipes

### Recipe 1: How to Add a New Sponsored Component
1. Open `catalogs/ad_catalog.json`.
2. Add your component definition under the `components` array with a unique `$id`.
3. Implement the corresponding Web Component renderer in `renderers/lit/your-component.ts`.
4. Update `google_a2a_agent/schemas/visual_renderer.py` to build the component in the A2UI surface.

### Recipe 2: How to Add an External Ad Network Provider
1. Open `google_a2a_agent/auction/ad_client.py`.
2. Implement your fetcher method (e.g. `_fetch_from_custom_network(query)`).
3. Normalize the response into the standard `AdResult` schema.
4. Hook it into `fetch_sponsored_cards()` with automatic reserve price and deduplication.

### Recipe 3: How to Run the Pytest Suite
```powershell
.venv\Scripts\pytest tests
```
All 31 unit tests will run, covering schemas, auctions, hooks, and multi-agent coordination.

