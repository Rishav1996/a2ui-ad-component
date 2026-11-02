"""
A2UI Ad Auction Package.
Implements the Vickrey second-price RTB ad exchange, live SerpApi search ads client,
and deterministic Google ADK lifecycle callbacks.
"""
from google_a2a_agent.auction.ad_sandbox import LocalAdExchangeSandbox, MOCK_CAMPAIGNS
from google_a2a_agent.auction.ad_client import (
    get_ad_network_client,
    classify_commercial_intent,
    BaseAdNetworkClient,
    LocalSandboxAdClient,
    RealSearchEngineAdClient,
)
from google_a2a_agent.auction.callbacks import (
    inject_a2ui_ad_callback,
    validate_a2ui_security_callback,
    AD_CATALOG_ID,
)

__all__ = [
    "LocalAdExchangeSandbox",
    "MOCK_CAMPAIGNS",
    "get_ad_network_client",
    "classify_commercial_intent",
    "BaseAdNetworkClient",
    "LocalSandboxAdClient",
    "RealSearchEngineAdClient",
    "inject_a2ui_ad_callback",
    "validate_a2ui_security_callback",
    "AD_CATALOG_ID",
]
