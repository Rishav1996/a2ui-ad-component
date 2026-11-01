"""
Google A2A Agent Package
Autonomous Multi-Agent Search and Contextual Ad Engine using Google ADK.
"""
from dotenv import load_dotenv

load_dotenv()

from google_a2a_agent.agent import (
    search_and_ad_coordinator,
    organic_search_agent,
    contextual_ad_agent,
    root_agent,
)
from google_a2a_agent.runner import execute_search_pipeline, execute_search_pipeline_async

__all__ = [
    "search_and_ad_coordinator",
    "organic_search_agent",
    "contextual_ad_agent",
    "root_agent",
    "execute_search_pipeline",
    "execute_search_pipeline_async",
]
