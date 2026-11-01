import json
from unittest.mock import MagicMock
import pytest
from google.adk.models import LlmResponse
from google.genai import types
from google_a2a_agent.ad_sandbox import LocalAdExchangeSandbox, MOCK_CAMPAIGNS
from google_a2a_agent.schema_manager import A2uiSchemaManager
from google_a2a_agent.callbacks import inject_a2ui_ad_callback, AD_CATALOG_ID

@pytest.fixture
def sandbox():
    return LocalAdExchangeSandbox()

@pytest.fixture
def schema_manager():
    return A2uiSchemaManager()

def test_realtime_auction_returns_top_3_distinct_winners(sandbox):
    winners = sandbox.execute_realtime_auction("Deploy DeepSeek-R1 models on serverless GPU containers", top_k=3)
    assert len(winners) == 3
    # Check uniqueness
    campaign_ids = [w["campaign_id"] for w in winners]
    assert len(set(campaign_ids)) == 3
    # Check clearing price is present
    for w in winners:
        assert "clearing_price_inr" in w
        assert w["clearing_price_inr"] > 0
        assert w["clearing_price_inr"] <= w["cpm_inr"]

def test_realtime_copy_personalization_deepseek(sandbox):
    winners = sandbox.execute_realtime_auction("Deploy DeepSeek on GPU", top_k=1)
    winner = winners[0]
    assert "deepseek" in winner["headline"].lower() or "deepseek" in winner.get("badge", "").lower()

def test_realtime_copy_personalization_vector_memory(sandbox):
    winners = sandbox.execute_realtime_auction("Fast vector search for multi-agent memory storage", top_k=3)
    # The winners should be vector database sponsors
    categories = [w.get("category") for w in winners]
    assert "vector_db" in categories

def test_sponsored_card_schema_validation(schema_manager):
    valid_card = {
        "SponsoredCard": {
            "sponsorName": {"literalString": "TensorDock Cloud"},
            "headline": {"literalString": "Run GPUs at 60% Lower Cost"},
            "bodyText": {"literalString": "Instant clusters with free credits."},
            "ctaLabel": {"literalString": "Claim ₹5,000"},
            "disclosureText": {"literalString": "Sponsored"},
            "badgeText": {"literalString": "Lowest Cost"},
            "clearingPrice": 420.0,
            "onClickAction": {
                "name": "apply_sponsored_offer",
                "context": {
                    "targetUrl": {"literalString": "https://tensordock.com/adk-promo"},
                    "campaignId": {"literalString": "camp_gpu_01"}
                }
            }
        }
    }
    is_valid, errors = schema_manager.validate_sponsored_card(valid_card)
    assert is_valid is True, f"Validation errors: {errors}"

def test_sponsored_card_missing_disclosure_fails(schema_manager):
    invalid_card = {
        "SponsoredCard": {
            "sponsorName": {"literalString": "TensorDock Cloud"},
            "headline": {"literalString": "Run GPUs"},
            "ctaLabel": {"literalString": "Click"},
            "onClickAction": {
                "name": "apply_sponsored_offer",
                "context": {"targetUrl": {"literalString": "https://tensordock.com"}}
            }
        }
    }
    is_valid, errors = schema_manager.validate_sponsored_card(invalid_card)
    assert is_valid is False
    assert any("disclosureText" in e for e in errors)

def test_3_card_search_surface_validation(schema_manager):
    surface_payload = {
        "createSurface": {
            "surfaceId": "search_results_surface",
            "supportedCatalogIds": [
                "https://a2ui.org/specification/v0_9/catalogs/basic_catalog.json",
                AD_CATALOG_ID
            ],
            "components": [
                {
                    "id": "search_gist_heading",
                    "component": {
                        "Heading": {"text": {"literalString": "Executive Search Gist"}, "level": 2}
                    }
                },
                {
                    "id": "search_gist_card",
                    "component": {
                        "Card": {
                            "title": {"literalString": "Key Takeaways"},
                            "content": {"literalString": "Serverless GPU containers scale to zero automatically."}
                        }
                    }
                },
                {
                    "id": "ad_1",
                    "component": {
                        "SponsoredCard": {
                            "sponsorName": {"literalString": "Sponsor 1"},
                            "headline": {"literalString": "Deal 1"},
                            "ctaLabel": {"literalString": "Get Offer"},
                            "disclosureText": {"literalString": "Sponsored"},
                            "onClickAction": {
                                "name": "click_1",
                                "context": {"targetUrl": {"literalString": "https://tensordock.com/1"}}
                            }
                        }
                    }
                },
                {
                    "id": "ad_2",
                    "component": {
                        "SponsoredCard": {
                            "sponsorName": {"literalString": "Sponsor 2"},
                            "headline": {"literalString": "Deal 2"},
                            "ctaLabel": {"literalString": "Get Offer"},
                            "disclosureText": {"literalString": "Sponsored"},
                            "onClickAction": {
                                "name": "click_2",
                                "context": {"targetUrl": {"literalString": "https://www.runpod.io/2"}}
                            }
                        }
                    }
                },
                {
                    "id": "ad_3",
                    "component": {
                        "SponsoredCard": {
                            "sponsorName": {"literalString": "Sponsor 3"},
                            "headline": {"literalString": "Deal 3"},
                            "ctaLabel": {"literalString": "Get Offer"},
                            "disclosureText": {"literalString": "Sponsored"},
                            "onClickAction": {
                                "name": "click_3",
                                "context": {"targetUrl": {"literalString": "https://lambdalabs.com/3"}}
                            }
                        }
                    }
                }
            ]
        }
    }

    res = schema_manager.validate_surface(surface_payload)
    assert res["valid"] is True, f"Validation errors: {res['errors']}"
    assert res["has_sponsored_cards"] is True
    assert res["sponsored_cards_count"] == 3

def test_inject_callback_appends_3_realtime_cards():
    mock_ctx = MagicMock()
    mock_ctx.state = {
        "supported_catalog_ids": [AD_CATALOG_ID],
        "ad_injected_this_turn": False,
        "ads_shown_count": 0,
    }
    mock_ctx.user_content = "Search for low latency vector databases for AI agents"
    mock_ctx.invocation_id = "test_search_turn_01"

    organic_gist = {
        "createSurface": {
            "surfaceId": "search_gist_surface",
            "components": [
                {
                    "id": "heading_1",
                    "component": {
                        "Heading": {"text": {"literalString": "Vector Databases Overview"}, "level": 1}
                    }
                }
            ]
        }
    }

    part = types.Part.from_text(text=json.dumps(organic_gist))
    content = types.Content(role="model", parts=[part])
    resp = LlmResponse(content=content)

    updated_resp = inject_a2ui_ad_callback(mock_ctx, resp)
    assert updated_resp is not None
    assert mock_ctx.state["ad_injected_this_turn"] is True
    assert mock_ctx.state["ads_shown_count"] == 3
    assert len(mock_ctx.state["realtime_auction_winners"]) == 3
    assert "app:ad_telemetry" in mock_ctx.state

    payload = json.loads(updated_resp.content.parts[0].text)
    surface = payload["createSurface"]
    components = surface["components"]
    # 1 organic heading + 3 sponsored cards = 4 components
    assert len(components) == 4
    ad_components = [c for c in components if "SponsoredCard" in c["component"]]
    assert len(ad_components) == 3

