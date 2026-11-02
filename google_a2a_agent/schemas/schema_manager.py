import json
import re
from pathlib import Path
from typing import Any, Optional
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

def _find_catalogs_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "catalogs",
        Path(__file__).resolve().parent.parent / "catalogs",
        Path.cwd() / "catalogs",
    ]
    for p in candidates:
        if p.exists() and (p / "common_types.json").exists():
            return p
    return candidates[0]


CATALOGS_DIR = _find_catalogs_dir()
COMMON_TYPES_PATH = CATALOGS_DIR / "common_types.json"
AD_CATALOG_PATH = CATALOGS_DIR / "ad_catalog.json"

BASIC_CATALOG_ID = "https://a2ui.org/specification/v0_9/catalogs/basic_catalog.json"
AD_CATALOG_ID = "https://a2ui.org/specification/v0_9/catalogs/custom/ad_catalog.json"
COMMON_TYPES_ID = "https://a2ui.org/specification/v0_9/common_types.json"

BASIC_CATALOG_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": BASIC_CATALOG_ID,
    "title": "A2UI Basic Component Catalog",
    "type": "object",
    "properties": {
        "Heading": {
            "type": "object",
            "properties": {
                "text": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
                "level": {"type": "integer", "minimum": 1, "maximum": 6}
            },
            "required": ["text"]
        },
        "Text": {
            "type": "object",
            "properties": {
                "text": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"}
            },
            "required": ["text"]
        },
        "Card": {
            "type": "object",
            "properties": {
                "title": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
                "content": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"}
            },
            "required": ["title", "content"]
        },
        "Button": {
            "type": "object",
            "properties": {
                "label": {"$ref": f"{COMMON_TYPES_ID}#/$defs/DynamicString"},
                "onClickAction": {"$ref": f"{COMMON_TYPES_ID}#/$defs/Action"}
            },
            "required": ["label", "onClickAction"]
        }
    }
}

class A2uiSchemaManager:
    """
    Manages A2UI v0.9 component catalogs, JSON schema validation,
    and system instruction authoring for Google ADK agents.
    """

    def __init__(self):
        self._load_catalogs()
        self._init_validator()

    def _load_catalogs(self) -> None:
        if COMMON_TYPES_PATH.exists():
            with open(COMMON_TYPES_PATH, "r", encoding="utf-8") as f:
                self.common_types = json.load(f)
        else:
            self.common_types = {"$defs": {}}

        if AD_CATALOG_PATH.exists():
            with open(AD_CATALOG_PATH, "r", encoding="utf-8") as f:
                self.ad_catalog = json.load(f)
        else:
            self.ad_catalog = {"$defs": {}}

        self.basic_catalog = BASIC_CATALOG_SCHEMA

    def _init_validator(self) -> None:
        res_common = Resource.from_contents(self.common_types)
        res_ad = Resource.from_contents(self.ad_catalog)
        res_basic = Resource.from_contents(self.basic_catalog)

        self.registry = Registry().with_resources([
            (COMMON_TYPES_ID, res_common),
            (AD_CATALOG_ID, res_ad),
            (BASIC_CATALOG_ID, res_basic),
        ])

        ad_banner_schema = self.ad_catalog.get("$defs", {}).get("AdBanner", {})
        self.ad_banner_validator = Draft202012Validator(
            ad_banner_schema, registry=self.registry
        )

        sponsored_card_schema = self.ad_catalog.get("$defs", {}).get("SponsoredCard", {})
        self.sponsored_card_validator = Draft202012Validator(
            sponsored_card_schema, registry=self.registry
        )

    def _validate_ad_component_common(
        self,
        component_node: dict[str, Any],
        component_name: str,
        validator: Draft202012Validator,
    ) -> tuple[bool, list[str]]:
        comp = component_node.get(component_name)
        if not comp or not isinstance(comp, dict):
            return False, [f"Missing '{component_name}' root key or payload is not a dictionary."]

        errors = []
        for err in validator.iter_errors(comp):
            errors.append(f"Validation error at path '{list(err.path)}': {err.message}")

        action = comp.get("onClickAction", {})
        context = action.get("context", {}) if isinstance(action, dict) else {}
        target_url = context.get("targetUrl") if isinstance(context, dict) else ""
        target_url_str = target_url.get("literalString", "") if isinstance(target_url, dict) else str(target_url or "")
        if target_url_str and not target_url_str.startswith("https://"):
            errors.append(f"Security violation: targetUrl must start with 'https://': {target_url_str}")

        disclosure = comp.get("disclosureText")
        disclosure_str = disclosure.get("literalString") if isinstance(disclosure, dict) else str(disclosure or "")
        if not disclosure_str or disclosure_str.strip().lower() not in ("sponsored", "ad", "promoted"):
            errors.append(f"Disclosure violation: disclosureText must be 'Sponsored', 'Ad', or 'Promoted'. Found: {disclosure_str}")

        return len(errors) == 0, errors

    def validate_ad_banner(self, component_node: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validates an AdBanner component dict against the v0.9 schema."""
        return self._validate_ad_component_common(component_node, "AdBanner", self.ad_banner_validator)

    def validate_sponsored_card(self, component_node: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validates a SponsoredCard component dict against the v0.9 schema."""
        return self._validate_ad_component_common(component_node, "SponsoredCard", self.sponsored_card_validator)

    def validate_surface(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Validates a full A2UI v0.9 surface message (createSurface or updateComponents).
        Supports Heading, Card, Text, Button, AdBanner, and SponsoredCard.
        """
        surface = payload.get("createSurface") or payload.get("updateComponents")
        if not surface or not isinstance(surface, dict):
            return {
                "valid": False,
                "errors": ["Payload does not contain a 'createSurface' or 'updateComponents' object."],
                "components": [],
                "has_ad_banner": False,
                "has_sponsored_cards": False,
                "sponsored_cards_count": 0,
                "ad_banner_valid": None,
            }

        components = surface.get("components")
        if not isinstance(components, list):
            return {
                "valid": False,
                "errors": ["Surface 'components' field must be a list."],
                "components": [],
                "has_ad_banner": False,
                "has_sponsored_cards": False,
                "sponsored_cards_count": 0,
                "ad_banner_valid": None,
            }

        component_names = []
        ad_banner_found = False
        sponsored_cards_count = 0
        validation_errors = []

        for node in components:
            if not isinstance(node, dict) or "component" not in node:
                continue
            comp = node["component"]
            for name, details in comp.items():
                component_names.append(name)
                if name == "AdBanner":
                    ad_banner_found = True
                    is_valid, errs = self.validate_ad_banner(comp)
                    if not is_valid:
                        validation_errors.extend(errs)
                elif name == "SponsoredCard":
                    sponsored_cards_count += 1
                    is_valid, errs = self.validate_sponsored_card(comp)
                    if not is_valid:
                        validation_errors.extend(errs)

        has_any_ad = ad_banner_found or (sponsored_cards_count > 0)
        return {
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "components": component_names,
            "has_ad_banner": ad_banner_found,
            "has_sponsored_cards": sponsored_cards_count > 0,
            "sponsored_cards_count": sponsored_cards_count,
            "ad_banner_valid": (len(validation_errors) == 0) if has_any_ad else None,
        }

    @staticmethod
    def extract_a2ui_json(text: str) -> Optional[dict[str, Any]]:
        """
        Extracts A2UI JSON payload from raw string or markdown fenced code blocks.
        """
        if not text:
            return None

        # Try direct JSON parsing
        try:
            parsed = json.loads(text.strip())
            if isinstance(parsed, dict) and ("createSurface" in parsed or "updateComponents" in parsed):
                return parsed
        except json.JSONDecodeError:
            pass

        # Try extracting ```json ... ``` block
        pattern = r"```(?:json)?\s*(\{[\s\S]*?\})\s*```"
        matches = re.findall(pattern, text)
        for m in matches:
            try:
                parsed = json.loads(m.strip())
                if isinstance(parsed, dict) and ("createSurface" in parsed or "updateComponents" in parsed):
                    return parsed
            except json.JSONDecodeError:
                continue

        # Try finding raw { "createSurface": ... } or { "updateComponents": ... }
        brace_pattern = r"(\{\s*\"(?:createSurface|updateComponents)\"[\s\S]*\})"
        brace_match = re.search(brace_pattern, text)
        if brace_match:
            try:
                parsed = json.loads(brace_match.group(1).strip())
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        return None

    def build_system_instruction(self, include_ad_catalog: bool = False) -> str:
        """
        Builds the system instruction for an A2UI agent.
        - If include_ad_catalog is True (Mode A): Prompt includes AdBanner schema and sponsorship instructions.
        - If False (Mode B): Prompt only includes BasicCatalog without any ad instructions.
        """
        base_instruction = (
            "You are an objective cloud infrastructure advisor.\n"
            "You communicate strictly by emitting a valid A2UI v0.9 JSON payload containing a `createSurface` message.\n"
            "A2UI v0.9 uses a flat adjacency list structure inside `components`:\n"
            "```json\n"
            "{\n"
            '  "createSurface": {\n'
            '    "surfaceId": "cloud_comparison_surface",\n'
            f'    "supportedCatalogIds": ["{BASIC_CATALOG_ID}"],\n'
            '    "components": [\n'
            '      {\n'
            '        "id": "comp_1",\n'
            '        "component": {\n'
            '          "Heading": {\n'
            '            "text": {"literalString": "Title Here"},\n'
            '            "level": 2\n'
            '          }\n'
            '        }\n'
            '      }\n'
            '    ]\n'
            '  }\n'
            "}\n"
            "```\n"
            "Standard components available in BasicCatalog: `Heading`, `Card`, `Text`, `Button`.\n"
            "Ensure all strings use the `{\"literalString\": \"...\"}` object format.\n"
        )

        if not include_ad_catalog:
            return (
                base_instruction +
                "\nProvide completely neutral, objective comparisons focusing solely on the user's technical query.\n"
                "Do NOT output promotional or sponsored material."
            )

        ad_instruction = (
            f"\nAdditionally, you have access to the AdBanner catalog ({AD_CATALOG_ID}).\n"
            "You MUST include an `AdBanner` component in your `createSurface.components` array.\n"
            "AdBanner requirements:\n"
            "- `sponsorName`: {\"literalString\": \"CloudScale GPU\"}\n"
            "- `headline`: {\"literalString\": \"Run 70B Open-Source Models with Zero Cold Starts\"}\n"
            "- `bodyText`: {\"literalString\": \"Claim ₹10,000 in free inference credits for your Google ADK agents.\"}\n"
            "- `ctaLabel`: {\"literalString\": \"Claim Free Credits\"}\n"
            "- `disclosureText`: {\"literalString\": \"Sponsored\"} (MANDATORY for transparency)\n"
            "- `mediaUrl`: {\"literalString\": \"https://www.google.com/s2/favicons?domain=tensordock.com&sz=128\"}\n"
            "- `onClickAction`: {\n"
            '    "name": "apply_sponsored_offer",\n'
            '    "context": {\n'
            '      "targetUrl": {"literalString": "https://tensordock.com/cloudscale-offer"},\n'
            '      "campaignId": {"literalString": "camp_adk_01"}\n'
            '    }\n'
            "  }\n"
            f'Add "{AD_CATALOG_ID}" to your `supportedCatalogIds` array.\n'
        )
        return base_instruction + ad_instruction

