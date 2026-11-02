from typing import Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

# Ensure .env (GOOGLE_API_KEY, SERPAPI_API_KEY, GEMINI_JUDGE_MODEL) is loaded before ADK init
load_dotenv()

from google.adk.cli.fast_api import get_fast_api_app
from google_a2a_agent.runner import (
    execute_search_pipeline,
    execute_search_pipeline_async,
    stream_search_pipeline_async,
    sandbox,
)
from google_a2a_agent.auction.ad_client import get_ad_network_client

# Resolve static web directory
STATIC_DIR = Path(__file__).resolve().parent / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# Google ADK Native Agent Server
# ==============================================================================
# Instantiates official Google ADK FastAPI server exposing native agent endpoints:
# - /run, /run_sse, /run_live
# - /apps/google_a2a_agent/run
# - /apps/google_a2a_agent/users/{user_id}/sessions
# - /list-apps, /health, /version
app = get_fast_api_app(
    agents_dir=".",
    web=False,
    allow_origins=["*"],
)


# ==============================================================================
# Pydantic Request & Response Schemas
# ==============================================================================
class SearchRequest(BaseModel):
    query: str = Field(..., description="The user search query.")
    session_id: Optional[str] = Field(None, description="Optional unique session identifier.")


class ClickRequest(BaseModel):
    session_id: str = Field(..., description="Session identifier where the click occurred.")
    campaign_id: str = Field(..., description="The campaign ID of the clicked ad.")


# ==============================================================================
# Search & Stream Log Endpoints
# ==============================================================================
@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "google_a2a_search_ad_api", "version": "2.0.0"}


@app.get("/api/chat/stream")
async def chat_stream_endpoint(query: str, session_id: Optional[str] = None):
    """
    Server-Sent Events (SSE) streaming endpoint for continuous multi-turn AI Chat.
    Streams real-time token deltas as Gemini synthesizes the answer, followed by
    the A2UI v0.9 SponsoredCard components and audit telemetry.
    """
    clean_query = (query or "").strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    return StreamingResponse(
        stream_search_pipeline_async(query=clean_query, session_id=session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/search")
def search_endpoint(req: SearchRequest) -> dict[str, Any]:
    """
    Executes the Google ADK multi-agent search pipeline (`search_and_ad_coordinator`):
    1. `organic_search_agent` produces an authentic, query-specific summary.
    2. `contextual_ad_agent` evaluates commercial intent and formats the A2UI v0.9 `createSurface` payload.
    3. Logs the query and triggered ads to SQLite for the real-time Stream Log.
    """
    query = (req.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        return execute_search_pipeline(query=query, session_id=req.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/click")
def click_endpoint(req: ClickRequest) -> dict[str, Any]:
    """Records user click on an A2UI SponsoredCard CTA button."""
    client = get_ad_network_client()
    client.log_click(
        session_id=req.session_id,
        campaign_id=req.campaign_id,
    )
    return {
        "status": "CLICK_RECORDED",
        "campaign_id": req.campaign_id,
        "session_id": req.session_id,
    }


@app.get("/api/analytics")
def analytics_endpoint() -> dict[str, Any]:
    """Returns the real-time Query-to-Ad stream log alongside live SerpApi & LLM quota health."""
    from google_a2a_agent.governance.quota_manager import quota_manager
    audit_log = sandbox.get_query_audits(limit=50)
    quota_health = quota_manager.get_global_health()
    return {
        "status": "SUCCESS",
        "audit_log": audit_log,
        "quota_health": quota_health,
    }


@app.post("/api/analytics/reset")
def reset_analytics_endpoint() -> dict[str, Any]:
    """Resets all query search logs and events for a clean session."""
    sandbox.clear_events()
    return {
        "status": "RESET_SUCCESSFUL",
        "audit_log": [],
    }


# ==============================================================================
# Static File Delivery (Frontend for Search & A2UI Stream)
# ==============================================================================
@app.get("/")
def serve_index() -> FileResponse:
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    raise HTTPException(status_code=404, detail="Frontend index.html not found.")


@app.get("/styles.css")
def serve_css() -> FileResponse:
    css_path = STATIC_DIR / "styles.css"
    if css_path.exists():
        return FileResponse(str(css_path), media_type="text/css")
    raise HTTPException(status_code=404, detail="styles.css not found.")


@app.get("/app.js")
def serve_js() -> FileResponse:
    js_path = STATIC_DIR / "app.js"
    if js_path.exists():
        return FileResponse(str(js_path), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found.")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
