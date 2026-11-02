import json
from typing import Any, Optional

AD_CATALOG_ID = "https://a2ui.org/specification/v0_9/catalogs/custom/ad_catalog.json"
BASIC_CATALOG_ID = "https://a2ui.org/specification/v0_9/catalogs/basic_catalog.json"


def render_visual_sponsored_cards_markdown(cards: list[dict[str, Any]]) -> str:
    """
    Renders styled, responsive visual cards for the ADK Web chat interface.
    Allows users to see cards with badges, prices, and clickable CTAs directly
    inside the chat window.
    """
    if not cards:
        return ""

    lines = [
        "---",
        "### 🏷️ Sponsored Recommendations",
        "> *Real-time Vickrey second-price auction results matched to your intent*",
        "",
    ]

    for idx, card in enumerate(cards, 1):
        sponsor = card.get("sponsor_name", "Sponsor")
        headline = card.get("headline", "Sponsored Solution")
        body = card.get("body", "")
        cta_label = card.get("cta_label", "Learn More")
        target_url = card.get("target_url", "#")
        badge = card.get("badge", "Featured")
        clearing_price = card.get("clearing_price_inr", 350.0)
        promo_code = card.get("promo_code", "")

        promo_badge = f"`Promo: {promo_code}` " if promo_code else ""

        card_block = (
            f"┌─────────────────────────────────────────────────────────────┐\n"
            f"│ **{sponsor}** &nbsp; `Sponsored` &nbsp; `🎯 {badge}`\n"
            f"│ **{headline}**\n"
            f"│ {body}\n"
            f"│ 💰 **Clearing CPM:** ₹{clearing_price:.2f}/1k impr &nbsp; {promo_badge}\n"
            f"│ 👉 [**{cta_label}**]({target_url})\n"
            f"└─────────────────────────────────────────────────────────────┘"
        )
        lines.append(card_block)
        lines.append("")

    return "\n".join(lines)


def build_sponsored_card_node(camp: dict[str, Any], idx: int) -> Optional[dict[str, Any]]:
    """Builds a canonical A2UI v0.9 SponsoredCard component node dictionary."""
    t_url = camp.get("target_url", "")
    m_url = camp.get("media_url", "")
    if not t_url.startswith("https://"):
        return None
    if m_url and not m_url.startswith("https://"):
        m_url = ""

    return {
        "id": f"sponsored_card_{idx+1}_{camp.get('campaign_id', idx)}",
        "component": {
            "SponsoredCard": {
                "sponsorName": {"literalString": camp.get("sponsor_name", "Sponsor")},
                "headline": {"literalString": camp.get("headline", "")},
                "bodyText": {"literalString": camp.get("body", "")},
                "ctaLabel": {"literalString": camp.get("cta_label", "Learn More")},
                "disclosureText": {"literalString": camp.get("disclosure", "Sponsored")},
                "mediaUrl": {"literalString": m_url},
                "badgeText": {"literalString": str(camp.get("badge", "Sponsored"))},
                "clearingPrice": float(camp.get("clearing_price_inr", 350.0)),
                "onClickAction": {
                    "name": "apply_sponsored_offer",
                    "context": {
                        "targetUrl": {"literalString": t_url},
                        "campaignId": {"literalString": str(camp.get("campaign_id", f"camp_{idx}"))},
                        "promoCode": {"literalString": camp.get("promo_code", "ADK_PROMO")},
                    },
                },
            }
        },
    }


def build_a2ui_search_surface(
    query_text: str,
    gist_text: str,
    cards: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Builds a canonical A2UI v0.9 `createSurface` dictionary containing the
    organic search gist components and the 3 SponsoredCard components.
    """
    components: list[dict[str, Any]] = [
        {
            "id": "search_gist_heading",
            "component": {
                "Heading": {
                    "text": {"literalString": f"Search Gist: {query_text[:50] if query_text else 'Results'}"},
                    "level": 2,
                }
            },
        },
        {
            "id": "search_gist_text",
            "component": {
                "Text": {
                    "text": {"literalString": gist_text[:800]}
                }
            },
        },
    ]

    for idx, camp in enumerate(cards):
        node = build_sponsored_card_node(camp, idx)
        if node:
            components.append(node)

    return {
        "createSurface": {
            "surfaceId": "search_results_surface",
            "supportedCatalogIds": [
                BASIC_CATALOG_ID,
                AD_CATALOG_ID,
            ],
            "components": components,
        }
    }
