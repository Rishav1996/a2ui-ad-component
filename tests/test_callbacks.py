import json
from unittest.mock import MagicMock
import pytest
from google.adk.models import LlmResponse
from google.genai import types
from google_a2a_agent.auction.callbacks import (
    AD_CATALOG_ID,
    inject_a2ui_ad_callback,
    validate_a2ui_security_callback,
)

@pytest.fixture
def mock_callback_context():
    ctx = MagicMock()
    ctx.state = {
        "supported_catalog_ids": [AD_CATALOG_ID],
        "ad_injected_this_turn": False,
        "ads_shown_count": 0,
    }
    return ctx

def create_mock_llm_response(text: str) -> LlmResponse:
    part = types.Part.from_text(text=text)
    content = types.Content(role="model", parts=[part])
    return LlmResponse(content=content)

def test_inject_ad_callback_success(mock_callback_context):
    mock_callback_context.state["active_sponsor"] = {
        "campaign_id": "camp_adk_01",
        "sponsor_name": "CloudScale GPU",
        "headline": "Run 70B Open-Source Models with Zero Cold Starts",
        "body": "Claim ₹10,000 in free inference credits.",
        "cta_label": "Claim Free Credits",
        "disclosure": "Sponsored",
        "target_url": "https://tensordock.com/cloudscale-offer",
        "media_url": "https://www.google.com/s2/favicons?domain=tensordock.com&sz=128",
    }
    organic_surface = {
        "createSurface": {
            "surfaceId": "test_surface",
            "supportedCatalogIds": ["https://a2ui.org/specification/v0_9/catalogs/basic_catalog.json"],
            "components": [
                {
                    "id": "heading_1",
                    "component": {
                        "Heading": {"text": {"literalString": "Organic Title"}, "level": 1}
                    }
                }
            ]
        }
    }
    response = create_mock_llm_response(json.dumps(organic_surface))

    updated_response = inject_a2ui_ad_callback(mock_callback_context, response)
    assert updated_response is not None
    assert mock_callback_context.state["ad_injected_this_turn"] is True
    assert mock_callback_context.state["ads_shown_count"] == 1
    assert "app:ad_telemetry" in mock_callback_context.state
    assert mock_callback_context.state["app:ad_telemetry"]["total_impressions"] >= 1

    payload = json.loads(updated_response.content.parts[0].text)
    surface = payload["createSurface"]
    assert AD_CATALOG_ID in surface["supportedCatalogIds"]

    components = surface["components"]
    assert len(components) == 2
    ad_node = components[1]
    assert "AdBanner" in ad_node["component"]
    ad = ad_node["component"]["AdBanner"]
    assert ad["disclosureText"]["literalString"] == "Sponsored"
    assert ad["onClickAction"]["context"]["targetUrl"]["literalString"].startswith("https://")

def test_inject_ad_frequency_capping(mock_callback_context):
    mock_callback_context.state["ad_injected_this_turn"] = True
    organic_surface = {
        "createSurface": {
            "surfaceId": "test_surface",
            "components": []
        }
    }
    response = create_mock_llm_response(json.dumps(organic_surface))

    result = inject_a2ui_ad_callback(mock_callback_context, response)
    assert result is None, "Should skip ad injection when frequency cap is active"

def test_inject_ad_unsupported_catalog_skipped(mock_callback_context):
    mock_callback_context.state["supported_catalog_ids"] = ["https://other.catalog.json"]
    organic_surface = {
        "createSurface": {
            "surfaceId": "test_surface",
            "components": []
        }
    }
    response = create_mock_llm_response(json.dumps(organic_surface))

    result = inject_a2ui_ad_callback(mock_callback_context, response)
    assert result is None, "Should skip injection when ad catalog is not negotiated"

def test_inject_ad_blocks_non_https(mock_callback_context):
    mock_callback_context.state["active_sponsor"] = {
        "campaign_id": "malicious_01",
        "sponsor_name": "Bad Actor",
        "headline": "Insecure Ad",
        "target_url": "http://insecure.tensordock.com/offer",
    }
    organic_surface = {"createSurface": {"components": []}}
    response = create_mock_llm_response(json.dumps(organic_surface))

    with pytest.raises(ValueError, match="Blocked non-HTTPS targetUrl"):
        inject_a2ui_ad_callback(mock_callback_context, response)

def test_validate_a2ui_security_callback_detects_xss(mock_callback_context):
    unsafe_text = '{"createSurface": {"action": "javascript:alert(1)"}}'
    response = create_mock_llm_response(unsafe_text)

    validate_a2ui_security_callback(mock_callback_context, response)
    violations = mock_callback_context.state.get("security_violations", [])
    assert any("XSS" in v for v in violations)

