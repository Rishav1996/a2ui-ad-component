"""
A2UI Schemas & Visual Surface Package.
Implements Draft 2020-12 offline JSON schema validation for A2UI v0.9 components
and builds surface adjacency lists and visual Markdown previews.
"""
from google_a2a_agent.schemas.schema_manager import A2uiSchemaManager
from google_a2a_agent.schemas.visual_renderer import (
    build_a2ui_search_surface,
    render_visual_sponsored_cards_markdown,
    AD_CATALOG_ID,
)

__all__ = [
    "A2uiSchemaManager",
    "build_a2ui_search_surface",
    "render_visual_sponsored_cards_markdown",
    "AD_CATALOG_ID",
]
