"""
Google ADK Server Launcher for A2UI & A2A Multi-Agent Engine.
Starts the unified ADK server exposing official ADK agent endpoints
(/run, /run_sse, /run_live, /apps/google_a2a_agent/run) alongside
the full A2UI Search & Stream Log Web interface.
"""
import sys
import uvicorn

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Starting Google ADK Server on http://127.0.0.1:{port} ...")
    uvicorn.run("web_app.server:app", host="127.0.0.1", port=port, reload=False)

