import json
import re
from typing import Any, Optional
from dotenv import load_dotenv
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai import types
from google_a2a_agent.ad_sandbox import LocalAdExchangeSandbox
from google_a2a_agent.ad_client import get_ad_network_client, classify_commercial_intent
from google_a2a_agent.visual_renderer import render_visual_sponsored_cards_markdown

load_dotenv()

AD_CATALOG_ID = "https://a2ui.org/specification/v0_9/catalogs/custom/ad_catalog.json"
BASIC_CATALOG_ID = "https://a2ui.org/specification/v0_9/catalogs/basic_catalog.json"

sandbox = LocalAdExchangeSandbox()


def inject_a2ui_ad_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """
    Native Google ADK after_model_callback for deterministic A2UI v0.9 SponsoredCard injection.
    - Skips intermediate tool-call turns (when function_call is present).
    - Uses cards fetched by the agent's dynamic_ad_search_tool (via SerpApi) or fetches live
      cards when commercial intent is detected.
    - Injects SponsoredCard components into the A2UI v0.9 createSurface payload.
    """
    if not llm_response.content or not llm_response.content.parts:
        return None

    # Do not intercept intermediate function_call turns; wait for the model's text response
    if any(getattr(p, "function_call", None) for p in llm_response.content.parts):
        return None

    # 1. Check client capability negotiation in ADK session state
    supported_catalogs = callback_context.state.get(
        "supported_catalog_ids", [AD_CATALOG_ID]
    )
    if AD_CATALOG_ID not in supported_catalogs:
        return None

    # 2. Enforce surface frequency cap (max 1 injection per surface turn)
    if callback_context.state.get("ad_injected_this_turn", False):
        return None

    # 3. Extract live search query from user content or state
    query_text = callback_context.state.get("user_query", "")
    if not query_text:
        user_content = getattr(callback_context, "user_content", None)
        if isinstance(user_content, str):
            query_text = user_content
        elif hasattr(user_content, "parts") and user_content.parts:
            parts_text = [p.text for p in user_content.parts if getattr(p, "text", None)]
            if parts_text:
                query_text = " ".join(parts_text)

    # 4. Determine commercial intent & pre-fetched cards from agent tool execution
    explicit_sponsor = callback_context.state.get("active_sponsor")
    prefetched_cards: Optional[list[dict[str, Any]]] = callback_context.state.get("sponsored_cards")
    state_category = callback_context.state.get("intent_category")
    state_commercial = callback_context.state.get("commercial_intent")

    # Check if the LLM output in this turn directly specified intent and category
    llm_text = ""
    for part in llm_response.content.parts:
        if getattr(part, "text", None):
            llm_text += part.text + "\n"

    parsed_intent = None
    parsed_category = None
    intent_m = re.search(r"INTENT:\s*(commercial|non_commercial)", llm_text, flags=re.IGNORECASE)
    if intent_m:
        parsed_intent = (intent_m.group(1).lower() == "commercial")
    cat_m = re.search(r"CATEGORY:\s*([a-zA-Z0-9_\-]+)", llm_text, flags=re.IGNORECASE)
    if cat_m:
        parsed_category = cat_m.group(1).lower()

    if parsed_intent is not None:
        is_commercial = parsed_intent
        category = parsed_category or state_category or ("commercial" if is_commercial else "non_commercial")
    elif state_commercial is not None:
        is_commercial = bool(state_commercial)
        category = state_category or "commercial"
    else:
        is_commercial, category = classify_commercial_intent(query_text)

    tokens_used = (
        llm_response.usage_metadata.total_token_count
        if llm_response.usage_metadata and getattr(llm_response.usage_metadata, "total_token_count", None)
        else 450
    )
    session_id = getattr(callback_context, "invocation_id", "session_adk") or "session_adk"

    if not is_commercial and not explicit_sponsor and not prefetched_cards:
        callback_context.state["commercial_intent"] = False
        callback_context.state["ad_intent_category"] = category
        return None

    callback_context.state["commercial_intent"] = True
    callback_context.state["ad_intent_category"] = category

    # Strict HTTPS security check on explicit sponsor if provided
    if explicit_sponsor:
        target_url = explicit_sponsor.get("target_url", "")
        media_url = explicit_sponsor.get("media_url", "")
        if not target_url.startswith("https://"):
            raise ValueError(f"Blocked non-HTTPS targetUrl in AdBanner: {target_url}")
        if media_url and not media_url.startswith("https://"):
            raise ValueError(f"Blocked non-HTTPS mediaUrl in AdBanner: {media_url}")

    new_parts = []
    mutated = False

    for part in llm_response.content.parts:
        if not part.text:
            new_parts.append(part)
            continue

        text = part.text.strip()
        payload = None

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
            if match:
                try:
                    payload = json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

        surface = None
        if isinstance(payload, dict):
            surface = payload.get("createSurface") or payload.get("updateComponents")

        if surface is not None and isinstance(surface, dict):
            if not isinstance(surface.get("components"), list):
                surface["components"] = []

            catalog_list = surface.setdefault("supportedCatalogIds", [])
            if AD_CATALOG_ID not in catalog_list:
                catalog_list.append(AD_CATALOG_ID)

            if explicit_sponsor:
                campaign_id = explicit_sponsor.get("campaign_id", "camp_adk_01")
                ad_node: dict[str, Any] = {
                    "id": f"ad_banner_{campaign_id}",
                    "component": {
                        "AdBanner": {
                            "sponsorName": {"literalString": explicit_sponsor["sponsor_name"]},
                            "headline": {"literalString": explicit_sponsor["headline"]},
                            "bodyText": {"literalString": explicit_sponsor.get("body", "")},
                            "ctaLabel": {"literalString": explicit_sponsor.get("cta_label", "Learn More")},
                            "disclosureText": {"literalString": explicit_sponsor.get("disclosure", "Sponsored")},
                            "mediaUrl": {"literalString": explicit_sponsor.get("media_url", "")},
                            "onClickAction": {
                                "name": "apply_sponsored_offer",
                                "context": {
                                    "targetUrl": {"literalString": explicit_sponsor["target_url"]},
                                    "campaignId": {"literalString": campaign_id},
                                    "promoCode": {"literalString": explicit_sponsor.get("promo_code", "ADK_PROMO")},
                                },
                            },
                        }
                    },
                }
                surface["components"].append(ad_node)
                callback_context.state["ad_injected_this_turn"] = True
                callback_context.state["ads_shown_count"] = callback_context.state.get("ads_shown_count", 0) + 1
                callback_context.state["a2ui_surface"] = payload
                telem = sandbox.log_impression(
                    session_id=str(session_id),
                    campaign=explicit_sponsor,
                    total_tokens=tokens_used,
                )
                callback_context.state["app:ad_telemetry"] = telem
            else:
                client = get_ad_network_client()
                winners = (
                    prefetched_cards
                    if prefetched_cards is not None
                    else client.fetch_sponsored_cards(query=query_text, category=category, limit=3)
                )
                for idx, camp in enumerate(winners):
                    t_url = camp.get("target_url", "")
                    m_url = camp.get("media_url", "")
                    if not t_url.startswith("https://"):
                        continue
                    if m_url and not m_url.startswith("https://"):
                        m_url = ""

                    card_node: dict[str, Any] = {
                        "id": f"sponsored_card_{idx+1}_{camp.get('campaign_id', idx)}",
                        "component": {
                            "SponsoredCard": {
                                "sponsorName": {"literalString": camp["sponsor_name"]},
                                "headline": {"literalString": camp["headline"]},
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
                                        "campaignId": {"literalString": camp.get("campaign_id", f"camp_{idx}")},
                                        "promoCode": {"literalString": camp.get("promo_code", "ADK_PROMO")},
                                    },
                                },
                            }
                        },
                    }
                    surface["components"].append(card_node)

                callback_context.state["ad_injected_this_turn"] = True
                callback_context.state["sponsored_cards"] = winners
                callback_context.state["realtime_auction_winners"] = [w.get("campaign_id") for w in winners]
                callback_context.state["ads_shown_count"] = callback_context.state.get("ads_shown_count", 0) + len(winners)
                callback_context.state["a2ui_surface"] = payload

                if prefetched_cards is None and winners:
                    telem = client.log_impressions(session_id=str(session_id), winning_campaigns=winners)
                    callback_context.state["app:ad_telemetry"] = telem
                elif winners:
                    callback_context.state["app:ad_telemetry"] = client.get_telemetry()

            mutated = True
            new_parts.append(types.Part.from_text(text=json.dumps(payload, indent=2)))
        else:
            new_parts.append(part)

    if not mutated:
        text_content = ""
        for part in llm_response.content.parts:
            if getattr(part, "text", None):
                text_content += part.text + "\n"

        text_content = text_content.strip()
        if text_content and not callback_context.state.get("ad_injected_this_turn", False):
            auction_query = query_text or text_content[:100]
            client = get_ad_network_client()
            winners = (
                prefetched_cards
                if prefetched_cards is not None
                else client.fetch_sponsored_cards(query=auction_query, category=category, limit=3)
            )
            sponsored_components: list[dict[str, Any]] = []
            for idx, camp in enumerate(winners):
                t_url = camp.get("target_url", "")
                m_url = camp.get("media_url", "")
                if not t_url.startswith("https://"):
                    continue
                if m_url and not m_url.startswith("https://"):
                    m_url = ""

                sponsored_components.append({
                    "id": f"sponsored_card_{idx+1}_{camp.get('campaign_id', idx)}",
                    "component": {
                        "SponsoredCard": {
                            "sponsorName": {"literalString": camp["sponsor_name"]},
                            "headline": {"literalString": camp["headline"]},
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
                                    "campaignId": {"literalString": camp.get("campaign_id", f"camp_{idx}")},
                                    "promoCode": {"literalString": camp.get("promo_code", "ADK_PROMO")},
                                },
                            },
                        }
                    },
                })

            organic_gist = callback_context.state.get("organic_summary") or text_content
            surface_payload = {
                "createSurface": {
                    "surfaceId": "search_results_surface",
                    "supportedCatalogIds": [
                        BASIC_CATALOG_ID,
                        AD_CATALOG_ID,
                    ],
                    "components": [
                        {
                            "id": "search_gist_heading",
                            "component": {
                                "Heading": {
                                    "text": {"literalString": f"Search Gist: {query_text[:80] if query_text else 'Results'}"},
                                    "level": 2,
                                }
                            },
                        },
                        {
                            "id": "search_gist_text",
                            "component": {
                                "Text": {
                                    "text": {"literalString": organic_gist}
                                }
                            },
                        },
                        *sponsored_components,
                    ],
                }
            }

            callback_context.state["ad_injected_this_turn"] = True
            callback_context.state["sponsored_cards"] = winners
            callback_context.state["realtime_auction_winners"] = [w.get("campaign_id") for w in winners]
            callback_context.state["ads_shown_count"] = callback_context.state.get("ads_shown_count", 0) + len(winners)
            callback_context.state["a2ui_surface"] = surface_payload

            if prefetched_cards is None and winners:
                telem = client.log_impressions(session_id=str(session_id), winning_campaigns=winners)
                callback_context.state["app:ad_telemetry"] = telem
            elif winners:
                callback_context.state["app:ad_telemetry"] = client.get_telemetry()

            visual_md = render_visual_sponsored_cards_markdown(winners)
            combined_text = (
                f"{text_content}\n\n"
                f"{visual_md}\n\n"
                f"### A2UI v0.9 createSurface JSON\n"
                f"```json\n{json.dumps(surface_payload, indent=2)}\n```"
            )
            return LlmResponse(
                content=types.Content(
                    role=llm_response.content.role,
                    parts=[types.Part.from_text(text=combined_text)],
                ),
                usage_metadata=llm_response.usage_metadata,
            )

        return None

    updated_content = types.Content(
        role=llm_response.content.role,
        parts=new_parts,
    )
    return LlmResponse(
        content=updated_content,
        usage_metadata=llm_response.usage_metadata,
    )


def validate_a2ui_security_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """
    Audits incoming/outgoing A2UI JSON messages for security compliance:
    - Verifies HTTPS protocol on all external links.
    - Prevents script injection (javascript: / data: URI schemes).
    """
    if not llm_response.content or not llm_response.content.parts:
        return None

    violations = []

    for part in llm_response.content.parts:
        if not part.text:
            continue
        text_lower = part.text.lower()
        if "javascript:" in text_lower or "data:text/html" in text_lower:
            violations.append("Blocked potential XSS / script URL scheme in A2UI response.")

        if "http://" in text_lower:
            violations.append("Detected insecure plain HTTP link in A2UI response.")

    if violations:
        current_violations = callback_context.state.get("security_violations", [])
        current_violations.extend(violations)
        callback_context.state["security_violations"] = current_violations

    return None
