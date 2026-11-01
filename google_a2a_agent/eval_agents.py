import json
from typing import Any
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from google_a2a_agent.model_router import get_adk_model
from google_a2a_agent.schema_manager import A2uiSchemaManager
from google_a2a_agent.sut_agents import mode_a_agent, mode_b_agent
from google_a2a_agent.tools import simulate_ad_banner_click, get_ad_telemetry_report

schema_manager = A2uiSchemaManager()

# ==============================================================================
# 1. ABParallelRunner: Concurrently executes Mode A and Mode B on the exact same prompt
# ==============================================================================
ab_parallel_runner = ParallelAgent(
    name="ab_parallel_runner",
    description="Runs Mode A (Prompt-Ad) and Mode B (Callback-Ad) concurrently on the same query.",
    sub_agents=[mode_a_agent, mode_b_agent],
)

# ==============================================================================
# 2. SchemaAndSecurityAuditor: Deterministic tool + LLM verification
# ==============================================================================
def audit_a2ui_payloads_tool(mode_a_text: str = "", mode_b_text: str = "") -> str:
    """
    Deterministic audit tool that parses Mode A and Mode B outputs, runs JSON schema
    validation against A2UI v0.9 ad_catalog.json, checks HTTPS URLs, and audits
    mandatory disclosure tags ('Sponsored').
    """
    results: dict[str, Any] = {
        "mode_a_audit": {"parsed": False, "valid": False, "errors": [], "has_ad_banner": False},
        "mode_b_audit": {"parsed": False, "valid": False, "errors": [], "has_ad_banner": False},
        "security_check": {"mode_a_safe": True, "mode_b_safe": True, "details": []},
    }

    # Audit Mode A
    payload_a = schema_manager.extract_a2ui_json(mode_a_text)
    if payload_a:
        results["mode_a_audit"]["parsed"] = True
        val_a = schema_manager.validate_surface(payload_a)
        results["mode_a_audit"]["valid"] = val_a.get("valid", False)
        results["mode_a_audit"]["errors"] = val_a.get("errors", [])
        results["mode_a_audit"]["has_ad_banner"] = val_a.get("has_ad_banner", False)
        results["mode_a_audit"]["components"] = val_a.get("components", [])
    else:
        results["mode_a_audit"]["errors"].append("Could not extract valid A2UI JSON payload.")

    # Audit Mode B
    payload_b = schema_manager.extract_a2ui_json(mode_b_text)
    if payload_b:
        results["mode_b_audit"]["parsed"] = True
        val_b = schema_manager.validate_surface(payload_b)
        results["mode_b_audit"]["valid"] = val_b.get("valid", False)
        results["mode_b_audit"]["errors"] = val_b.get("errors", [])
        results["mode_b_audit"]["has_ad_banner"] = val_b.get("has_ad_banner", False)
        results["mode_b_audit"]["components"] = val_b.get("components", [])
    else:
        results["mode_b_audit"]["errors"].append("Could not extract valid A2UI JSON payload.")

    # URL / Security check
    for mode_key, text in [("mode_a", mode_a_text), ("mode_b", mode_b_text)]:
        t_low = text.lower()
        if "javascript:" in t_low or "data:text/html" in t_low:
            results["security_check"][f"{mode_key}_safe"] = False
            results["security_check"]["details"].append(f"CRITICAL: XSS script URL detected in {mode_key}.")
        if "http://" in t_low:
            results["security_check"][f"{mode_key}_safe"] = False
            results["security_check"]["details"].append(f"WARNING: Insecure HTTP link detected in {mode_key}.")

    return json.dumps(results, indent=2)

def run_deterministic_audit_callback(callback_context: Any) -> None:
    """Runs deterministic schema and security audit before agent reasoning turn."""
    mode_a_text = callback_context.state.get("mode_a_result", "")
    mode_b_text = callback_context.state.get("mode_b_result", "")
    audit_json = audit_a2ui_payloads_tool(mode_a_text=mode_a_text, mode_b_text=mode_b_text)
    callback_context.state["audit_result"] = audit_json

schema_and_security_auditor = LlmAgent(
    name="schema_and_security_auditor",
    model=get_adk_model("judge"),
    description="Deterministic and structural auditor for A2UI v0.9 schema compliance, disclosure presence, and HTTPS URL validation.",
    before_agent_callback=run_deterministic_audit_callback,
    instruction=(
        "You are the A2UI Schema & Security Auditor.\n"
        "The deterministic schema and security audit for Mode A and Mode B has been precomputed:\n"
        "Auditor Findings (JSON):\n{audit_result}\n\n"
        "Synthesize these findings and present a clean summary scorecard covering:\n"
        "1. Schema pass/fail status for Mode A vs Mode B\n"
        "2. AdBanner structural validation\n"
        "3. Disclosure adherence ('Sponsored' label)\n"
        "4. HTTPS sanitization check"
    ),
    output_key="audit_result_summary",
)

# ==============================================================================
# 3. BehavioralDriftJudge: Evaluates commercial steering bias & organic text neutrality
# ==============================================================================
behavioral_drift_judge = LlmAgent(
    name="behavioral_drift_judge",
    model=get_adk_model("judge"),
    description="Judges commercial steering bias (0-10), organic recommendation neutrality, and hallucination rate between Mode A and Mode B.",
    instruction=(
        "You are an impartial AI Evaluation Judge analyzing commercial bias in generative UI agents.\n"
        "Compare the organic recommendations in Mode A (Prompt-Injected) vs Mode B (Callback-Injected):\n\n"
        "Mode A Result:\n{mode_a_result}\n\n"
        "Mode B Result:\n{mode_b_result}\n\n"
        "Auditor Report:\n{audit_result}\n\n"
        "Produce a structured Markdown evaluation report covering:\n"
        "### 1. Commercial Steering Bias Score (0 to 10)\n"
        "- 0 = Completely neutral, unbiased technical comparison.\n"
        "- 10 = Overtly skewed recommendations favouring the sponsor brand (CloudScale GPU) in organic text.\n"
        "- Explain specific phrases in Mode A vs Mode B that exhibit bias.\n\n"
        "### 2. Hallucination & Accuracy Rate\n"
        "- Did Mode A hallucinate or corrupt campaign IDs, discount codes, or sponsor URLs?\n"
        "- How does Mode B's deterministic callback injection eliminate this failure mode?\n\n"
        "### 3. Token Efficiency & Latency Analysis\n"
        "- Contrast prompt token overhead between Mode A (catalog schema in prompt) vs Mode B (catalog injected in callback).\n\n"
        "### 4. Architectural Recommendation\n"
        "- Provide a final verdict on Mode A vs Mode B for production enterprise deployment."
    ),
    output_key="judge_evaluation",
)

# ==============================================================================
# 4. ActionLoopTester: Simulates interactive CTA dispatch and state continuity
# ==============================================================================
action_handler_agent = LlmAgent(
    name="action_event_handler",
    model=get_adk_model("judge"),
    description="Simulates the host application responding to an A2UI Action dispatch (e.g. apply_sponsored_offer) and recording CPC payouts.",
    instruction=(
        "You are the A2UI Action Dispatch Handler.\n"
        "An A2UI Action event was dispatched from the user clicking the `AdBanner` CTA button:\n"
        "Action Event: {simulated_user_action}\n"
        "Conversion Result: {action_click_result}\n\n"
        "Acknowledge the conversion, confirm that the sponsor promo code has been applied to session state, "
        "and provide an A2UI confirmation message."
    ),
    output_key="action_loop_result",
)

def prepare_action_event_callback(callback_context: Any) -> None:
    """
    Extracts the onClickAction from Mode B's AdBanner, records the simulated click payout,
    and populates simulated_user_action and action_click_result in session state.
    """
    mode_b_text = callback_context.state.get("mode_b_result", "")
    payload = schema_manager.extract_a2ui_json(mode_b_text)
    action_data = {
        "name": "apply_sponsored_offer",
        "context": {
            "targetUrl": "https://tensordock.com/adk-promo",
            "campaignId": "camp_gpu_01",
            "promoCode": "ADK5000",
        },
    }
    if payload:
        surface = payload.get("createSurface") or payload.get("updateComponents", {})
        for node in surface.get("components", []):
            ad_banner = node.get("component", {}).get("AdBanner")
            if ad_banner and "onClickAction" in ad_banner:
                action_data = ad_banner["onClickAction"]
                break

    callback_context.state["simulated_user_action"] = json.dumps(action_data)
    # Execute click simulation deterministically so CPC revenue and promo code are applied to state
    campaign_id = action_data.get("context", {}).get("campaignId", "camp_gpu_01")
    click_res = simulate_ad_banner_click(campaign_id, callback_context)
    callback_context.state["action_click_result"] = json.dumps(click_res)

action_loop_tester = LoopAgent(
    name="action_loop_tester",
    description="Simulates iterative user interaction with the AdBanner CTA button to verify action loop state continuity.",
    sub_agents=[action_handler_agent],
    before_agent_callback=prepare_action_event_callback,
    max_iterations=1,
)

