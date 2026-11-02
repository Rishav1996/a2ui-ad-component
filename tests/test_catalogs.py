import json
from pathlib import Path
import pytest
from google_a2a_agent.schemas.schema_manager import A2uiSchemaManager

CATALOGS_DIR = Path(__file__).resolve().parent.parent / "catalogs"

@pytest.fixture
def schema_manager():
    return A2uiSchemaManager()

def test_ad_catalog_file_exists():
    catalog_path = CATALOGS_DIR / "ad_catalog.json"
    assert catalog_path.exists(), "ad_catalog.json must exist"
    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "$id" in data
    assert "$defs" in data
    assert "AdBanner" in data["$defs"]

def test_sponsored_card_example_validation(schema_manager):
    example_path = CATALOGS_DIR / "ad_examples" / "sponsored_card.json"
    assert example_path.exists(), "sponsored_card.json must exist"
    with open(example_path, "r", encoding="utf-8") as f:
        example_payload = json.load(f)

    result = schema_manager.validate_surface(example_payload)
    assert result["valid"] is True, f"Validation errors: {result['errors']}"
    assert result["has_ad_banner"] is True
    assert "AdBanner" in result["components"]

def test_ad_banner_missing_disclosure_fails(schema_manager):
    invalid_node = {
        "AdBanner": {
            "sponsorName": {"literalString": "Test Corp"},
            "headline": {"literalString": "Fast GPUs"},
            "ctaLabel": {"literalString": "Click"},
            # Missing mandatory disclosureText
            "onClickAction": {
                "name": "click_ad",
                "context": {"targetUrl": {"literalString": "https://tensordock.com"}}
            }
        }
    }
    is_valid, errors = schema_manager.validate_ad_banner(invalid_node)
    assert is_valid is False
    assert any("disclosureText" in e for e in errors)

def test_ad_banner_insecure_target_url_fails(schema_manager):
    invalid_node = {
        "AdBanner": {
            "sponsorName": {"literalString": "Insecure Corp"},
            "headline": {"literalString": "Cheap Hosting"},
            "ctaLabel": {"literalString": "Click"},
            "disclosureText": {"literalString": "Sponsored"},
            "onClickAction": {
                "name": "click_ad",
                "context": {"targetUrl": {"literalString": "http://insecure.tensordock.com"}}
            }
        }
    }
    is_valid, errors = schema_manager.validate_ad_banner(invalid_node)
    assert is_valid is False
    assert any("https://" in e for e in errors)

