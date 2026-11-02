from typing import Any, Optional
from dotenv import load_dotenv
from google.adk.tools.tool_context import ToolContext
from google_a2a_agent.auction.ad_client import get_ad_network_client

load_dotenv()


def search_knowledge_tool(query: str, tool_context: Optional[ToolContext] = None) -> dict[str, Any]:
    """
    Retrieves live objective web search results and factual knowledge via DuckDuckGo.
    This tool is 100% organic with zero advertising.
    If web search yields no live snippets or is unreachable, it returns empty fields
    so the Gemini LLM Agent synthesizes an authentic, domain-accurate response directly
    from its own knowledge base (ZERO canned or dummy strings).
    """
    clean_query = (query or "").strip()
    sources = []
    highlights = []
    gist = ""

    try:
        from duckduckgo_search import DDGS
        with DDGS(timeout=5) as ddgs:
            raw_results = list(ddgs.text(clean_query, max_results=4))
            for res in raw_results:
                title = (res.get("title") or "").strip()
                snippet = (res.get("body") or "").strip()
                href = (res.get("href") or "").strip()
                if snippet:
                    highlights.append(f"{title}: {snippet}")
                    sources.append({"title": title, "url": href, "snippet": snippet})
            if highlights:
                gist = " ".join(highlights[:2])
    except Exception:
        pass

    result = {
        "query": clean_query,
        "search_status": "SUCCESS" if gist else "NO_WEB_RESULTS_USE_LLM_KNOWLEDGE",
        "search_engine": "DuckDuckGo",
        "gist": gist,
        "highlights": highlights,
        "sources": sources,
    }
    if tool_context and hasattr(tool_context, "state"):
        tool_context.state["last_search_result"] = result
        if sources:
            tool_context.state["search_sources"] = sources

    return result


def fetch_sponsored_cards_tool(
    query: str,
    category: str = "commercial",
    entity_queries: Optional[list[str]] = None,
    max_cards: int = 3,
    region: Optional[str] = None,
    location: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """
    Dynamically fetches live commercial sponsored cards from SerpApi (Google Paid Search Ads & Google Shopping).
    Should ONLY be invoked when commercial, shopping, product, or service intent exists.
    Pass:
      - query: Primary commercial search phrase (e.g. focused on key entities identified from refined organic content).
      - category: Specific commercial intent category.
      - entity_queries: (Optional) List of specific brand or product entity search strings extracted from content.
      - max_cards: Maximum number of cards to return (default 3).
      - region: Country code for regional targeting (e.g. 'us', 'in').
      - location: Location name (e.g. 'New York, United States').
    """
    client = get_ad_network_client()
    winning_cards = client.fetch_sponsored_cards(
        query=query,
        category=category,
        entity_queries=entity_queries,
        limit=max_cards,
        region=region,
        location=location,
    )

    session_id = "session_tool_call"
    if tool_context:
        session_id = str(getattr(tool_context, "invocation_id", "session_tool_call"))

    if winning_cards:
        client.log_impressions(
            session_id=session_id,
            winning_campaigns=winning_cards,
        )

    if tool_context and hasattr(tool_context, "state"):
        tool_context.state["sponsored_cards"] = winning_cards
        tool_context.state["intent_category"] = category
        tool_context.state["commercial_intent"] = True if winning_cards else False
        tool_context.state["realtime_auction_winners"] = [c.get("campaign_id") for c in winning_cards]

    return {
        "status": "ADS_RETRIEVED" if winning_cards else "NO_ADS_FOUND",
        "query": query,
        "category": category,
        "cards_count": len(winning_cards),
        "cards": winning_cards,
    }


dynamic_ad_search_tool = fetch_sponsored_cards_tool


def simulate_ad_banner_click(
    campaign_id: str,
    tool_context: Optional[ToolContext] = None,
    session_id: str = "session_tool_call",
    sponsor_name: str = "Sponsored Partner",
    promo_code: str = "ADK_PROMO",
) -> dict[str, Any]:
    """Records a user clicking on a sponsored card CTA."""
    client = get_ad_network_client()
    if tool_context and hasattr(tool_context, "invocation_id"):
        session_id = str(tool_context.invocation_id)

    telemetry = client.log_click(session_id=session_id, campaign_id=campaign_id)

    if tool_context and hasattr(tool_context, "state"):
        tool_context.state["active_promo_code"] = promo_code
        tool_context.state["app:ad_telemetry"] = telemetry

    return {
        "status": "CLICK_LOGGED",
        "campaign_id": campaign_id,
        "a2ui_action_status": "DISPATCHED_SUCCESSFULLY",
        "applied_promo_code": promo_code,
        "sponsor": sponsor_name,
    }


def get_ad_telemetry_report(tool_context: Optional[ToolContext] = None) -> dict[str, Any]:
    """Returns audit log summary."""
    client = get_ad_network_client()
    telemetry = client.get_telemetry()
    if tool_context and hasattr(tool_context, "state"):
        tool_context.state["app:ad_telemetry"] = telemetry
    return telemetry
