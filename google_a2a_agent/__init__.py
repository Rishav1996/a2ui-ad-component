"""
A2UI Ad Component & Multi-Agent Engine.
A production-grade Google ADK framework implementing A2UI v0.9 Commercial UI Components
with real-time second-price Vickrey auctions, content-grounded educational gating,
and live SSE token streaming.
"""
from dotenv import load_dotenv

load_dotenv()

# Subpackage exports
from google_a2a_agent import auction, agents, governance, schemas, tools

# Multi-Agent exports
from google_a2a_agent.agents.coordinator import (
    search_and_ad_coordinator,
    organic_search_agent,
    contextual_ad_agent,
    root_agent,
    benchmark_pipeline,
)

# Runner & Streaming exports
from google_a2a_agent.runner import (
    execute_search_pipeline,
    execute_search_pipeline_async,
    stream_search_pipeline_async,
    get_shared_runner,
)

# Ad Exchange & Auction exports
from google_a2a_agent.auction.ad_sandbox import LocalAdExchangeSandbox, MOCK_CAMPAIGNS
from google_a2a_agent.auction.ad_client import get_ad_network_client, classify_commercial_intent
from google_a2a_agent.auction.callbacks import inject_a2ui_ad_callback, validate_a2ui_security_callback

# Governance & Quota exports
from google_a2a_agent.governance.quota_manager import quota_manager, QuotaManager
from google_a2a_agent.governance.model_router import get_adk_model

# Schema & Visual exports
from google_a2a_agent.schemas.schema_manager import A2uiSchemaManager
from google_a2a_agent.schemas.visual_renderer import build_a2ui_search_surface, AD_CATALOG_ID

__all__ = [
    # Subpackages
    "auction",
    "agents",
    "governance",
    "schemas",
    "tools",
    # Agents
    "search_and_ad_coordinator",
    "organic_search_agent",
    "contextual_ad_agent",
    "root_agent",
    "benchmark_pipeline",
    # Runner & Streaming
    "execute_search_pipeline",
    "execute_search_pipeline_async",
    "stream_search_pipeline_async",
    "get_shared_runner",
    # Auction & Exchange
    "LocalAdExchangeSandbox",
    "MOCK_CAMPAIGNS",
    "get_ad_network_client",
    "classify_commercial_intent",
    "inject_a2ui_ad_callback",
    "validate_a2ui_security_callback",
    # Governance
    "quota_manager",
    "QuotaManager",
    "get_adk_model",
    # Schemas
    "A2uiSchemaManager",
    "build_a2ui_search_surface",
    "AD_CATALOG_ID",
]
