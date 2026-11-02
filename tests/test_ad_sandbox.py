import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from google_a2a_agent.auction.ad_sandbox import LocalAdExchangeSandbox
from google_a2a_agent.tools.ad_tools import simulate_ad_banner_click, get_ad_telemetry_report

@pytest.fixture
def temp_sandbox():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = Path(f.name)
    sandbox = LocalAdExchangeSandbox(db_path=temp_path)
    yield sandbox
    try:
        temp_path.unlink()
    except Exception:
        pass

def test_log_impression_and_token_cost(temp_sandbox):
    camp = {
        "campaign_id": "test_camp_01",
        "sponsor_name": "Test Cloud",
        "cpm_inr": 480.0,
        "clearing_price_inr": 480.0,
    }
    cpm = float(camp["cpm_inr"])
    expected_rev = cpm / 1000.0
    summary = temp_sandbox.log_impression(session_id="test_sess_01", campaign=camp, total_tokens=1000)

    assert summary["total_impressions"] == 1
    assert summary["total_clicks"] == 0
    assert summary["ctr_percent"] == "0.0%"
    assert summary["total_tokens_processed"] == 1000

    # 1000 tokens at ₹0.025/1k = ₹0.025 cost
    assert summary["llm_inference_cost_inr"] == "₹0.0250"
    assert summary["gross_ad_revenue_inr"] == f"₹{expected_rev:.2f}"
    assert float(summary["net_margin_inr"].replace("₹", "")) > 0.40

def test_log_click_and_ctr(temp_sandbox):
    camp = {
        "campaign_id": "test_camp_02",
        "sponsor_name": "Test Cloud",
        "cpm_inr": 480.0,
        "clearing_price_inr": 480.0,
        "cpc_inr": 42.0,
    }
    cpm = float(camp["cpm_inr"])
    cpc = float(camp["cpc_inr"])
    expected_rev = (cpm / 1000.0) + cpc
    temp_sandbox.log_impression(session_id="test_sess_02", campaign=camp, total_tokens=500)
    summary_click = temp_sandbox.log_click(
        session_id="test_sess_02",
        campaign_id=camp["campaign_id"],
        sponsor_name=camp["sponsor_name"],
        cpc_inr=cpc,
    )

    assert summary_click["total_impressions"] == 1
    assert summary_click["total_clicks"] == 1
    assert summary_click["ctr_percent"] == "100.0%"
    assert f"₹{expected_rev:.2f}" in summary_click["gross_ad_revenue_inr"]

def test_simulate_ad_banner_click_tool():
    tool_ctx = MagicMock()
    tool_ctx.state = {}
    tool_ctx.invocation_id = "test_tool_turn"

    res = simulate_ad_banner_click(
        "camp_gpu_01",
        tool_ctx,
        sponsor_name="TensorDock Cloud",
        promo_code="ADK5000",
    )
    assert res["a2ui_action_status"] == "DISPATCHED_SUCCESSFULLY"
    assert res["applied_promo_code"] == "ADK5000"
    assert res["sponsor"] == "TensorDock Cloud"
    assert tool_ctx.state["active_promo_code"] == "ADK5000"
    assert "app:ad_telemetry" in tool_ctx.state

def test_get_ad_telemetry_report_tool():
    tool_ctx = MagicMock()
    tool_ctx.state = {}

    summary = get_ad_telemetry_report(tool_ctx)
    assert "total_impressions" in summary
    assert "gross_ad_revenue_inr" in summary
    assert tool_ctx.state["app:ad_telemetry"] == summary
