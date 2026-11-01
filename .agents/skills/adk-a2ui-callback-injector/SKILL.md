---
name: adk-a2ui-callback-injector
description: Implements deterministic, hook-based ad and UI injection into A2UI responses using native Google ADK callbacks and session state.
---

# ADK A2UI Callback Injector

## Overview
This skill governs the implementation of deterministic, lifecycle-hook injection of A2UI components (Mode B). Instead of prompting the LLM to generate ads or commercial recommendations, an ADK `after_model_callback` intercepts the organic model output and mutates the A2UI surface message deterministically.

## Core Rules & Guardrails

1. **Exact ADK Hook Signature:**
   ```python
   def inject_a2ui_ad_callback(
       callback_context: CallbackContext,
       llm_response: LlmResponse
   ) -> Optional[LlmResponse]:
   ```
   - Returning `None` preserves the original `llm_response` without mutation.
   - Returning a new or modified `LlmResponse` overrides the model output.

2. **Session State & Client Capability Negotiation:**
   - Read client capabilities from `callback_context.state.get("supported_catalog_ids", [])`.
   - Only inject an `AdBanner` if `https://a2ui.org/specification/v0_9/catalogs/custom/ad_catalog.json` is negotiated.
   - Read frequency cap state: `callback_context.state.get("ad_injected_this_turn", False)`.
   - Increment or set tracking metrics in `callback_context.state` (e.g. `state["ads_shown_count"] += 1`).

3. **Deterministic Structure Modification:**
   - Parse `llm_response.content.parts` to locate JSON payloads containing `createSurface` or `updateComponents`.
   - Append the `AdBanner` node to `surface["components"]`.
   - Update parent container's `children` list if a root container layout is present.
   - Re-serialize JSON preserving proper formatting.

4. **Security & Sanitization:**
   - Mandatory check: All promotional URLs (`targetUrl`, `mediaUrl`) MUST use secure `https://` protocols.
   - Reject or block any `javascript:`, `data:`, or plaintext `http://` URLs.
   - Locked disclosure text: The `disclosureText` field must always be set deterministically to `"Sponsored"` (or localized compliance equivalent) and cannot be tampered with by the LLM.

5. **Token and Cost Preservation:**
   - Mode B completely eliminates prompt token bloat associated with ad catalog schemas and few-shot examples in system instructions.
   - Mode B prevents model steering bias because the organic inference turn is 100% focused on user intent.

