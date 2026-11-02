"""
Vercel Serverless Function entrypoint for A2UI v0.9 Commercial UI & Google ADK Multi-Agent Server.
Exposes the FastAPI ASGI application for @vercel/python.
"""
import sys
from pathlib import Path

# Add project root directory to sys.path so modules and catalogs resolve cleanly in Vercel
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import the production FastAPI app
from web_app.server import app

# Expose app for Vercel ASGI handler
__all__ = ["app"]
