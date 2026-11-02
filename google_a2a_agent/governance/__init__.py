"""
A2UI Governance Package.
Implements live API quota governance for Google Gemini LLM and SerpApi,
alongside hybrid LiteLLM and Google AI Studio model provider routing.
"""
from google_a2a_agent.governance.quota_manager import quota_manager, QuotaManager
from google_a2a_agent.governance.model_router import (
    get_adk_model,
    get_gemini_rate_limit_config,
    DEFAULT_GEMINI_MODEL,
)

__all__ = [
    "quota_manager",
    "QuotaManager",
    "get_adk_model",
    "get_gemini_rate_limit_config",
    "DEFAULT_GEMINI_MODEL",
]

