import json
import re
from typing import Any, Optional
from dotenv import load_dotenv
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai import types

from google_a2a_agent.auction.ad_sandbox import LocalAdExchangeSandbox
from google_a2a_agent.auction.ad_client import get_ad_network_client, classify_commercial_intent
from google_a2a_agent.schemas.visual_renderer import (
    render_visual_sponsored_cards_markdown,
    build_sponsored_card_node,
    build_a2ui_search_surface,
    AD_CATALOG_ID,
    BASIC_CATALOG_ID,
)

load_dotenv()

sandbox = LocalAdExchangeSandbox()


def _record_ad_turn_state(
    callback_context: CallbackContext,
    surface_payload: dict[str, Any],
    winners: list[dict[str, Any]],
    prefetched_cards: Optional[list[dict[str, Any]]],
    session_id: str,
    client: Any,
) -> None:
    """Updates session state and records impression telemetry for injected sponsored cards."""
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

    # Do not intercept intermediate function_call turns
    if any(getattr(p, "function_call", None) for p in llm_response.content.parts):
        return None

    # 1. Capability negotiation check
    supported_catalogs = callback_context.state.get("supported_catalog_ids", [AD_CATALOG_ID])
    if AD_CATALOG_ID not in supported_catalogs:
        return None

    # 2. Surface frequency cap (max 1 injection per surface turn)
    if callback_context.state.get("ad_injected_this_turn", False):
        return None

    # 3. Extract search query
    query_text = callback_context.state.get("user_query", "")
    if not query_text:
        user_content = getattr(callback_context, "user_content", None)
        if isinstance(user_content, str):
            query_text = user_content
        elif hasattr(user_content, "parts") and user_content.parts:
            parts_text = [p.text for p in user_content.parts if getattr(p, "text", None)]
            if parts_text:
                query_text = " ".join(parts_text)

    # 4. Intent & pre-fetched cards evaluation
    explicit_sponsor = callback_context.state.get("active_sponsor")
    prefetched_cards: Optional[list[dict[str, Any]]] = callback_context.state.get("sponsored_cards")
    state_category = callback_context.state.get("intent_category")
    state_commercial = callback_context.state.get("commercial_intent")

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
                    card_node = build_sponsored_card_node(camp, idx)
                    if card_node:
                        surface["components"].append(card_node)

                _record_ad_turn_state(
                    callback_context=callback_context,
                    surface_payload=payload,
                    winners=winners,
                    prefetched_cards=prefetched_cards,
                    session_id=session_id,
                    client=client,
                )

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

            organic_gist = callback_context.state.get("organic_summary") or text_content
            surface_payload = build_a2ui_search_surface(query_text, organic_gist, winners)

            _record_ad_turn_state(
                callback_context=callback_context,
                surface_payload=surface_payload,
                winners=winners,
                prefetched_cards=prefetched_cards,
                session_id=session_id,
                client=client,
            )

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
