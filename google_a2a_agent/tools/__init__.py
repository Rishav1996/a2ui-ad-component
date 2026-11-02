"""
A2UI Executable Tools Package.
Implements Google ADK executable tools for CTA simulation, live telemetry reporting,
web knowledge search, and dynamic sponsored card retrieval.
"""
from google_a2a_agent.tools.ad_tools import (
    simulate_ad_banner_click,
    get_ad_telemetry_report,
    search_knowledge_tool,
    fetch_sponsored_cards_tool,
    dynamic_ad_search_tool,
)

__all__ = [
    "simulate_ad_banner_click",
    "get_ad_telemetry_report",
    "search_knowledge_tool",
    "fetch_sponsored_cards_tool",
    "dynamic_ad_search_tool",
]
