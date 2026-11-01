"""
Google ADK Server Launcher for A2UI & A2A Multi-Agent Engine.
Starts the unified ADK server exposing official ADK agent endpoints
(/run, /run_sse, /run_live, /apps/google_a2a_agent/run) alongside
the full A2UI Search & Stream Log Web interface.
"""
import os
import sys
import uvicorn

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    default_port = int(os.getenv("PORT", "8000"))
    port = int(sys.argv[1]) if len(sys.argv) > 1 else default_port
    print(f"Starting Google ADK Server on http://{host}:{port} ...")
    uvicorn.run("web_app.server:app", host=host, port=port, reload=False)

