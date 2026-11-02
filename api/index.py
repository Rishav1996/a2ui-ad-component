"""
Vercel Serverless Function entrypoint for A2UI v0.9 Commercial UI & Google ADK Multi-Agent Server.
Exposes the FastAPI ASGI application for @vercel/python.
"""
import os
import sys
import tempfile
from pathlib import Path

# Add project root directory to sys.path so modules and catalogs resolve cleanly in Vercel
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# On Vercel / serverless runtimes, the deployment root directory is read-only.
# Ensure SQLite telemetry database writes to cross-platform temporary scratch storage (/tmp on Linux).
if "AD_TELEMETRY_DB_PATH" not in os.environ:
    os.environ["AD_TELEMETRY_DB_PATH"] = str(Path(tempfile.gettempdir()) / "ad_telemetry.db")

# Import the production FastAPI app
from web_app.server import app

# Expose app for Vercel ASGI handler
__all__ = ["app"]

