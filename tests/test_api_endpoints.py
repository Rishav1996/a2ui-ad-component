import pytest
from web_app.server import (
    health_check,
    search_endpoint,
    click_endpoint,
    analytics_endpoint,
    reset_analytics_endpoint,
    SearchRequest,
    ClickRequest,
    sandbox,
)


@pytest.fixture(autouse=True)
def clean_sandbox_events():
    try:
        sandbox.clear_events()
    except Exception:
        pass
    yield
    try:
        sandbox.clear_events()
    except Exception:
        pass


def test_health_endpoint():
    data = health_check()
    assert data["status"] == "ok"
    assert data["service"] == "google_a2a_search_ad_api"


def test_api_search_commercial_query():
    # 'what is GPU' is commercial hardware intent
    req = SearchRequest(query="what is GPU")
    data = search_endpoint(req)

    assert data["status"] == "SUCCESS"
    assert data["is_commercial"] is True
    assert data["intent_category"] == "gpu_compute"
    assert len(data["organic_summary"]) > 10
    assert data["cards_count"] == 3
    assert len(data["cards"]) == 3
    assert all("sponsor_name" in c for c in data["cards"])

    # Verify A2UI v0.9 surface
    surface = data["a2ui_surface"]
    assert "createSurface" in surface
    components = surface["createSurface"]["components"]
    assert any("SponsoredCard" in c["component"] for c in components)


def test_api_search_educational_query():
    # 'how do trees produce oxygen' is educational science intent
    req = SearchRequest(query="how do trees produce oxygen")
    data = search_endpoint(req)

    assert data["status"] == "SUCCESS"
    assert data["is_commercial"] is False
    assert data["intent_category"] == "educational_concept"
    assert len(data["organic_summary"]) > 10
    assert data["cards_count"] == 0
    assert len(data["cards"]) == 0


def test_api_search_watches_top_3_tier_query():
    # 'Can you tell me which watches are top 3 tier'
    req = SearchRequest(query="Can you tell me which watches are top 3 tier")
    data = search_endpoint(req)

    assert data["status"] == "SUCCESS"
    assert data["is_commercial"] is True
    # ZERO DUMMY DATA VERIFICATION: Never output fake latency/throughput boilerplate!
    summary = data["organic_summary"].lower()
    assert "latency" not in summary
    assert "throughput" not in summary
    assert "operational efficiency trade-offs" not in summary
    # Domain authenticity check
    assert any(name in summary for name in ["patek", "audemars", "vacheron", "holy trinity", "watch"])
    assert data["cards_count"] == 3


def test_web_app_server_routes():
    from web_app.server import (
        health_check as web_health,
        search_endpoint as web_search,
        SearchRequest as WebSearchRequest,
    )
    h = web_health()
    assert h["status"] == "ok"
    assert h["service"] == "google_a2a_search_ad_api"

    res = web_search(WebSearchRequest(query="Can you tell me which watches are top 3 tier"))
    assert res["status"] == "SUCCESS"
    assert "latency" not in res["organic_summary"].lower()


def test_api_click_endpoint():
    req = ClickRequest(session_id="test_click_sess", campaign_id="camp_gpu_01")
    data = click_endpoint(req)

    assert data["status"] == "CLICK_RECORDED"
    assert data["campaign_id"] == "camp_gpu_01"


def test_api_analytics_dashboard_endpoint():
    # Run a commercial query first
    search_endpoint(SearchRequest(query="what is GPU"))

    data = analytics_endpoint()
    assert "kpis" not in data
    assert "audit_log" in data

    # Check query-to-ad audit log table format
    audit_log = data["audit_log"]
    assert len(audit_log) >= 1
    entry = audit_log[0]
    assert entry["query_text"] == "what is GPU"
    assert entry["is_commercial"] is True
    assert entry["ads_count"] == 3
    assert len(entry["ads_summary"]) == 3


def test_api_reset_analytics_endpoint():
    # Perform a query
    search_endpoint(SearchRequest(query="what is GPU"))

    # Reset
    data = reset_analytics_endpoint()
    assert data["status"] == "RESET_SUCCESSFUL"

    # Verify stream log is reset
    ana_data = analytics_endpoint()
    assert "kpis" not in ana_data
    assert len(ana_data["audit_log"]) == 0
