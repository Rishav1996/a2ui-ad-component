import json
from unittest.mock import MagicMock
import pytest
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from google_a2a_agent.agents.coordinator import root_agent, benchmark_pipeline, search_ad_agent, organic_search_agent, contextual_ad_agent
from google_a2a_agent.agents.eval_agents import (
    ab_parallel_runner,
    audit_a2ui_payloads_tool,
    behavioral_drift_judge,
    prepare_action_event_callback,
    schema_and_security_auditor,
    action_loop_tester,
)
from google_a2a_agent.agents.sut_agents import mode_a_agent, mode_b_agent

def test_pipeline_architecture():
    # Verify root_agent is the coordinated multi-agent system separating organic search from contextual ads
    assert isinstance(root_agent, SequentialAgent)
    assert root_agent.name == "search_and_ad_coordinator"
    sub_names = [a.name for a in root_agent.sub_agents]
    assert sub_names == ["organic_search_agent", "contextual_ad_agent"]

    organic_agent = root_agent.sub_agents[0]
    ad_agent = root_agent.sub_agents[1]

    # Organic agent: neutral, no ad callback
    assert organic_agent.after_model_callback is None
    assert any("search_knowledge_tool" in getattr(t, "__name__", "") for t in organic_agent.tools)

    # Ad agent: intent gating & ad injection callback
    assert ad_agent.after_model_callback is not None
    assert any(("sponsored" in getattr(t, "__name__", "") or "ad" in getattr(t, "__name__", "")) for t in ad_agent.tools)

    # Verify the benchmark pipeline is configured for multi-agent evaluation
    assert isinstance(benchmark_pipeline, SequentialAgent)
    sub_agent_names = [agent.name for agent in benchmark_pipeline.sub_agents]
    assert sub_agent_names == [
        "ab_parallel_runner",
        "schema_and_security_auditor",
        "behavioral_drift_judge",
        "action_loop_tester",
    ]

def test_parallel_runner_composition():
    assert isinstance(ab_parallel_runner, ParallelAgent)
    assert len(ab_parallel_runner.sub_agents) == 2
    assert mode_a_agent.output_key == "mode_a_result"
    assert mode_b_agent.output_key == "mode_b_result"
    assert mode_b_agent.after_model_callback is not None

def test_schema_manager_prompt_differences():
    # Mode A prompt should contain AdBanner catalog instructions
    assert "AdBanner" in mode_a_agent.instruction
    assert "Sponsored" in mode_a_agent.instruction

    # Mode B prompt should NOT contain AdBanner instructions
    assert "AdBanner" not in mode_b_agent.instruction
    assert "CloudScale GPU" not in mode_b_agent.instruction

def test_audit_tool_execution():
    valid_payload = json.dumps({
        "createSurface": {
            "surfaceId": "test_surf",
            "supportedCatalogIds": ["https://a2ui.org/specification/v0_9/catalogs/custom/ad_catalog.json"],
            "components": [
                {
                    "id": "ad_1",
                    "component": {
                        "AdBanner": {
                            "sponsorName": {"literalString": "Test Sponsor"},
                            "headline": {"literalString": "Fast Compute"},
                            "ctaLabel": {"literalString": "Get Started"},
                            "disclosureText": {"literalString": "Sponsored"},
                            "onClickAction": {
                                "name": "click_ad",
                                "context": {"targetUrl": {"literalString": "https://sponsor.com"}}
                            }
                        }
                    }
                }
            ]
        }
    })

    audit_str = audit_a2ui_payloads_tool(mode_a_text=valid_payload, mode_b_text=valid_payload)
    report = json.loads(audit_str)
    assert report["mode_a_audit"]["valid"] is True
    assert report["mode_b_audit"]["valid"] is True
    assert report["security_check"]["mode_a_safe"] is True
    assert report["security_check"]["mode_b_safe"] is True

def test_prepare_action_event_callback():
    ctx = MagicMock()
    ctx.state = {
        "mode_b_result": json.dumps({
            "createSurface": {
                "components": [
                    {
                        "component": {
                            "AdBanner": {
                                "onClickAction": {
                                    "name": "apply_sponsored_offer",
                                    "context": {"campaignId": "camp_adk_01"}
                                }
                            }
                        }
                    }
                ]
            }
        })
    }
    prepare_action_event_callback(ctx)
    assert "simulated_user_action" in ctx.state
    action = json.loads(ctx.state["simulated_user_action"])
    assert action["name"] == "apply_sponsored_offer"
    assert action["context"]["campaignId"] == "camp_adk_01"

