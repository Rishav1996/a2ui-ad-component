import json
from unittest.mock import MagicMock
import pytest
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai import types

from google_a2a_agent.ad_client import (
    classify_commercial_intent,
    LocalSandboxAdClient,
    RealHttpAdServerClient,
    get_ad_network_client,
)
from google_a2a_agent.visual_renderer import (
    render_visual_sponsored_cards_markdown,
    build_a2ui_search_surface,
)
from google_a2a_agent.tools import search_knowledge_tool, fetch_sponsored_cards_tool
from google_a2a_agent.callbacks import inject_a2ui_ad_callback, AD_CATALOG_ID


def test_intent_classification_informational_queries():
    # Casual, educational, or syntax queries must be classified as non-commercial
    informational_samples = [
        "What is Python?",
        "hi",
        "hello there",
        "how to write a for loop",
        "explain quicksort in python",
        "how do trees produce oxygen",
        "how does photosynthesis work",
        "why is the sky blue",
        "2 + 2",
        "tell me a joke",
    ]
    for q in informational_samples:
        is_comm, reason = classify_commercial_intent(q)
        assert not is_comm, f"Query '{q}' was incorrectly flagged as commercial: {reason}"


def test_intent_classification_commercial_queries():
    # Queries comparing, evaluating, or asking about commercial hardware/products must trigger ads
    commercial_samples = [
        ("what is GPU", "gpu_compute"),
        ("what is a GPU", "gpu_compute"),
        ("what is a vector database", "vector_db"),
        ("what is H100", "gpu_compute"),
        ("Compare DeepSeek-R1 vs Qwen-2.5 on serverless GPUs", "gpu_compute"),
        ("What are the best vector databases for multi-agent RAG memory?", "vector_db"),
        ("Recommend LLM evaluation and drift tracing tools", "observability"),
        ("Cheapest cloud GPU provider for vLLM", "gpu_compute"),
        ("Book cheap flights to London", "travel_hospitality"),
        ("Compare car insurance quotes online", "financial_insurance"),
        ("Best CRM software for startup sales", "saas_software"),
        ("Best online courses to learn python", "education_careers"),
        ("Best laptop for software engineering", "consumer_products"),
    ]
    for q, expected_cat in commercial_samples:
        is_comm, category = classify_commercial_intent(q)
        assert is_comm, f"Query '{q}' should be commercial."
        assert category == expected_cat, f"Expected {expected_cat}, got {category}"


def test_local_sandbox_ad_client():
    client = LocalSandboxAdClient()
    cards = client.fetch_sponsored_cards(query="serverless GPUs for DeepSeek", limit=3)
    assert len(cards) == 3
    assert all("sponsor_name" in c for c in cards)
    assert all("clearing_price_inr" in c for c in cards)
    assert any("DeepSeek" in c.get("badge", "") for c in cards)


def test_real_http_ad_server_client_fallback():
    # If external ad server is unreachable, it should fall back to local auction
    client = RealHttpAdServerClient(
        endpoint_url="https://unreachable-ad-network.internal.net/v1/bids",
        timeout_seconds=0.1,
    )
    cards = client.fetch_sponsored_cards(query="serverless GPUs", limit=3)
    assert len(cards) == 3
    assert cards[0]["sponsor_name"] is not None


def test_visual_cards_markdown_renderer():
    sample_cards = [
        {
            "sponsor_name": "TensorDock Cloud",
            "headline": "Deploy H100 at 60% Lower Cost",
            "body": "Zero cold start Kubernetes nodes.",
            "cta_label": "Claim Credit",
            "target_url": "https://tensordock.com/promo",
            "badge": "DeepSeek Optimized",
            "clearing_price_inr": 441.0,
            "promo_code": "ADK5000",
        }
    ]
    rendered = render_visual_sponsored_cards_markdown(sample_cards)
    assert "TensorDock Cloud" in rendered
    assert "DeepSeek Optimized" in rendered
    assert "441.00" in rendered
    assert "https://tensordock.com/promo" in rendered


def test_build_a2ui_search_surface():
    sample_cards = [
        {
            "sponsor_name": "TensorDock Cloud",
            "headline": "Deploy H100",
            "body": "Zero cold start.",
            "cta_label": "Claim Credit",
            "target_url": "https://tensordock.com/promo",
            "badge": "Featured",
            "clearing_price_inr": 441.0,
            "campaign_id": "camp_1",
        }
    ]
    surface = build_a2ui_search_surface("Test Query", "Test Gist", sample_cards)
    assert "createSurface" in surface
    components = surface["createSurface"]["components"]
    assert len(components) == 3  # Heading + Text + 1 SponsoredCard
    assert components[0]["component"]["Heading"]["text"]["literalString"] == "Search Gist: Test Query"
    assert components[2]["component"]["SponsoredCard"]["sponsorName"]["literalString"] == "TensorDock Cloud"


def test_search_and_ad_tools_separated():
    # 1. Search tool returns pure organic technical summary
    search_res = search_knowledge_tool("Compare serverless GPUs for DeepSeek")
    assert search_res["search_status"] == "SUCCESS"
    assert "H100" in search_res["gist"]
    assert "cards" not in search_res  # Zero ads in search tool

    # 2. Ad tool explicitly retrieves sponsored cards
    ad_res = fetch_sponsored_cards_tool("Compare serverless GPUs for DeepSeek", max_cards=3)
    assert ad_res["status"] == "ADS_RETRIEVED"
    assert len(ad_res["cards"]) == 3


def test_callback_intent_gating_blocks_informational_queries():
    # If user query is informational, callback must NOT inject any ads!
    mock_context = MagicMock(spec=CallbackContext)
    mock_context.state = {
        "supported_catalog_ids": [AD_CATALOG_ID],
        "ad_injected_this_turn": False,
    }
    mock_context.user_content = "What is Python?"

    llm_resp = LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text="Python is a high-level programming language.")],
        )
    )

    result = inject_a2ui_ad_callback(mock_context, llm_resp)
    assert result is None  # Blocked from injecting ads
    assert mock_context.state.get("commercial_intent") is False
    assert mock_context.state.get("ad_injected_this_turn", False) is False


def test_callback_intent_gating_allows_commercial_queries():
    # If user query is commercial, callback must inject 3 sponsored cards!
    mock_context = MagicMock(spec=CallbackContext)
    mock_context.state = {
        "supported_catalog_ids": [AD_CATALOG_ID],
        "ad_injected_this_turn": False,
    }
    mock_context.user_content = "Compare DeepSeek-R1 vs Qwen-2.5 on serverless GPUs"

    llm_resp = LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text="DeepSeek-R1 is optimized for reasoning latency on serverless GPUs.")],
        )
    )

    result = inject_a2ui_ad_callback(mock_context, llm_resp)
    assert result is not None
    assert mock_context.state.get("commercial_intent") is True
    assert mock_context.state.get("ad_injected_this_turn") is True
    assert len(mock_context.state.get("realtime_auction_winners", [])) == 3

    # Verify visual markdown card block and A2UI JSON exist in the returned text
    response_text = result.content.parts[0].text
    assert "Sponsored Recommendations" in response_text
    assert "TensorDock Cloud" in response_text
    assert "A2UI v0.9 createSurface JSON" in response_text


def test_callback_what_is_gpu_injects_ads():
    # 'what is GPU' must be recognized as commercial hardware intent and trigger 3 ads
    mock_context = MagicMock(spec=CallbackContext)
    mock_context.state = {
        "supported_catalog_ids": [AD_CATALOG_ID],
        "ad_injected_this_turn": False,
    }
    mock_context.user_content = "what is GPU"

    llm_resp = LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text="A GPU (Graphics Processing Unit) is a specialized processor for parallel compute.")],
        )
    )

    result = inject_a2ui_ad_callback(mock_context, llm_resp)
    assert result is not None
    assert mock_context.state.get("commercial_intent") is True
    assert mock_context.state.get("ad_intent_category") == "gpu_compute"
    assert mock_context.state.get("ad_injected_this_turn") is True
    assert len(mock_context.state.get("realtime_auction_winners", [])) == 3

    response_text = result.content.parts[0].text
    assert "Sponsored Recommendations" in response_text
    assert "TensorDock Cloud" in response_text


def test_multivertical_ad_card_retrieval():
    client = get_ad_network_client()

    # 1. Travel search retrieves travel sponsors
    travel_cards = client.fetch_sponsored_cards("cheap flights to London", limit=3)
    assert len(travel_cards) > 0
    assert any(c["category"] == "travel_hospitality" for c in travel_cards)

    # 2. Insurance search retrieves insurance sponsors
    insurance_cards = client.fetch_sponsored_cards("car insurance quotes", limit=3)
    assert len(insurance_cards) > 0
    assert any(c["category"] == "financial_insurance" for c in insurance_cards)

    # 3. SaaS CRM search retrieves software sponsors
    crm_cards = client.fetch_sponsored_cards("best CRM software for startups", limit=3)
    assert len(crm_cards) > 0
    assert any(c["category"] == "saas_software" for c in crm_cards)

    # 4. Strictly non-commercial query returns ZERO ads
    bio_cards = client.fetch_sponsored_cards("how do trees produce oxygen", limit=3)
    assert len(bio_cards) == 0



