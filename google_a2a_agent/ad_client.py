import json
import os
import re
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Optional
from dotenv import load_dotenv
from google_a2a_agent.ad_sandbox import LocalAdExchangeSandbox

load_dotenv()

# Commercial keywords for heuristic fallback classification when needed
COMMERCIAL_INTENT_KEYWORDS = {
    # Purchase & Evaluation
    "compare", "comparison", "vs", "versus", "best", "top", "tier", "recommend", "recommendation",
    "pricing", "price", "cost", "cheap", "alternative", "alternatives", "review", "reviews",
    "buy", "shop", "order", "deal", "deals", "discount", "quote", "quotes", "brand", "brands",
    "luxury", "premium", "affordable", "store",
    # Watches, Fashion & Luxury Goods
    "watch", "watches", "wacthes", "rolex", "patek", "audemars", "vacheron", "omega", "cartier",
    "seiko", "casio", "timepiece", "chronograph", "horology", "jewelry",
    # Infrastructure & Compute
    "gpu", "gpus", "h100", "l40s", "a100", "rtx", "nvidia", "amd", "radeon", "graphics",
    "cloud", "serverless", "cluster", "kubernetes", "hosting", "host", "deploy", "deployment",
    "provider", "providers", "vllm", "inference",
    # Data & Database
    "database", "vectordb", "vector", "qdrant", "pinecone", "weaviate", "milvus", "embedding",
    "rag", "storage",
    # Observability & Monitoring
    "observability", "tracing", "eval", "evals", "telemetry", "monitor", "monitoring",
    "phoenix", "langfuse", "arize", "datadog", "newrelic",
    # Models in Commercial Deployment
    "deepseek", "qwen", "mistral", "llama",
    # Travel & Flights
    "flight", "flights", "airline", "airlines", "ticket", "tickets", "hotel", "hotels", "stay",
    "travel", "vacation", "trip", "booking", "skyscanner", "emirates",
    # Finance, Insurance & Legal
    "insurance", "car", "auto", "policy", "coverage", "loan", "mortgage", "bank", "banking",
    "incorporate", "incorporation", "c-corp", "llc", "stripe", "atlas", "geico", "progressive",
    # SaaS & Business
    "crm", "leads", "sales", "hubspot", "monday", "linear", "jira", "kanban", "workflow", "management",
    "software", "saas", "platform", "tool", "tools", "app", "apps",
    # Education & Learning
    "course", "courses", "learn", "bootcamp", "certificate", "certification", "degree",
    "coursera", "datacamp", "udemy",
    # Consumer Goods & Electronics
    "laptop", "laptops", "macbook", "asus", "zenbook", "computer", "pc", "shoes", "shoe",
    "sneakers", "nike", "running", "keyboard", "monitor", "headphones", "phone", "iphone", "samsung",
}

# Casual chat & trivial stop patterns with zero commercial intent
CASUAL_CHAT_PATTERNS = [
    r"^(hi|hello|hey|yo|greetings|good\s+morning|good\s+afternoon|good\s+evening|how\s+are\s+you)\b",
    r"^\d+\s*[\+\-\*\/]\s*\d+",
    r"^tell\s+me\s+a\s+joke",
    r"^who\s+(are\s+you|created\s+you|is\s+your)\b",
]

# Non-commercial educational, scientific, and basic programming syntax queries
NON_COMMERCIAL_CONCEPT_PATTERNS = [
    r"^(what\s+is|explain|how\s+to\s+write|what\s+does)\s+(a|an|the)?\s*(for\s+loop|while\s+loop|function|syntax|variable|math|quicksort|bubble\s+sort|binary\s+search|recursion|python|decorator)",
    r"^what\s+is\s+python\b",
    r"^(how|why)\s+(do|does|is|are)\s+(photosynthesis|trees|plants|volcanoes|earthquakes|gravity|water\s+cycle|blood\s+cells|atoms)",
    r"how\s+do\s+trees\s+produce\s+oxygen",
]


def classify_commercial_intent(query: str) -> tuple[bool, str]:
    """
    Heuristic classifier for commercial vs non-commercial intent.
    """
    if not query or not query.strip():
        return False, "empty_query"

    clean_query = query.strip().lower()

    for pat in CASUAL_CHAT_PATTERNS:
        if re.search(pat, clean_query):
            return False, "casual_chat"

    for pat in NON_COMMERCIAL_CONCEPT_PATTERNS:
        if re.search(pat, clean_query):
            return False, "educational_concept"

    tokens = set(re.findall(r"[a-z0-9_\-]+", clean_query))
    matched_keywords = tokens.intersection(COMMERCIAL_INTENT_KEYWORDS)

    if matched_keywords:
        if any(k in matched_keywords for k in ["watch", "watches", "wacthes", "rolex", "patek", "audemars", "vacheron", "omega", "cartier", "seiko", "casio", "timepiece", "chronograph", "horology", "jewelry"]):
            return True, "luxury_watches"
        elif any(k in matched_keywords for k in ["gpu", "gpus", "h100", "l40s", "a100", "rtx", "nvidia", "amd", "radeon", "graphics", "serverless", "cloud", "deploy", "vllm", "cluster", "hosting"]):
            return True, "gpu_compute"
        elif any(k in matched_keywords for k in ["vector", "vectordb", "database", "qdrant", "rag", "embedding"]):
            return True, "vector_db"
        elif any(k in matched_keywords for k in ["laptop", "laptops", "macbook", "asus", "zenbook", "shoes", "shoe", "sneakers", "nike", "running", "keyboard", "monitor", "headphones", "phone", "iphone", "samsung"]):
            return True, "consumer_products"
        elif any(k in matched_keywords for k in ["flight", "flights", "hotel", "hotels", "airline", "airlines", "travel", "vacation", "booking", "skyscanner", "emirates"]):
            return True, "travel_hospitality"
        elif any(k in matched_keywords for k in ["insurance", "policy", "quote", "geico", "progressive", "incorporate", "incorporation", "atlas", "llc", "c-corp", "loan", "mortgage"]):
            return True, "financial_insurance"
        elif any(k in matched_keywords for k in ["crm", "sales", "leads", "hubspot", "monday", "linear", "jira", "workflow", "kanban", "saas", "software"]):
            return True, "saas_software"
        elif any(k in matched_keywords for k in ["course", "courses", "learn", "bootcamp", "coursera", "datacamp", "udemy", "certificate", "certification"]):
            return True, "education_careers"
        elif any(k in matched_keywords for k in ["eval", "tracing", "observability", "telemetry", "monitor"]):
            return True, "observability"
        return True, "commercial"

    return False, "non_commercial"


class BaseAdNetworkClient(ABC):
    """Abstract interface for querying ad inventory."""

    @abstractmethod
    def fetch_sponsored_cards(
        self,
        query: str,
        category: str = "general",
        entity_queries: Optional[list[str]] = None,
        limit: int = 3,
        region: Optional[str] = None,
        location: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def log_impressions(self, session_id: str, winning_campaigns: list[dict[str, Any]]) -> dict[str, Any]:
        pass

    @abstractmethod
    def log_click(self, session_id: str, campaign_id: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_telemetry(self) -> dict[str, Any]:
        pass


class LocalSandboxAdClient(BaseAdNetworkClient):
    """
    Offline test sandbox client (used only by explicit unit tests when testing local auction math).
    """

    def __init__(self, sandbox: Optional[LocalAdExchangeSandbox] = None):
        self.sandbox = sandbox or LocalAdExchangeSandbox()

    def fetch_sponsored_cards(
        self,
        query: str,
        category: str = "general",
        entity_queries: Optional[list[str]] = None,
        limit: int = 3,
        region: Optional[str] = None,
        location: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        return self.sandbox.execute_realtime_auction(search_query=query, top_k=limit, category=category)

    def log_impressions(self, session_id: str, winning_campaigns: list[dict[str, Any]]) -> dict[str, Any]:
        return self.sandbox.log_batch_impressions(session_id, winning_campaigns)

    def log_click(self, session_id: str, campaign_id: str) -> dict[str, Any]:
        return self.sandbox.log_click(session_id, campaign_id)

    def get_telemetry(self) -> dict[str, Any]:
        return self.sandbox.get_telemetry_summary()


class RealSearchEngineAdClient(BaseAdNetworkClient):
    """
    Dynamic Search Engine Ad Client powered by SerpApi (Google Search Ads & Google Shopping).
    Strictly prohibits returning hardcoded MOCK_CAMPAIGNS (CloudScale GPU / GEICO / MacBook)
    in production searches.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: float = 8.0,
        endpoint_url: str = "https://serpapi.com/search.json",
    ):
        load_dotenv()
        self.api_key = (api_key if api_key is not None else os.getenv("SERPAPI_API_KEY", "")).strip()
        self.timeout_seconds = timeout_seconds
        self.endpoint_url = endpoint_url
        self.sandbox = LocalAdExchangeSandbox()

    def _fetch_from_http_endpoint(self, query: str, category: str, limit: int = 3) -> list[dict[str, Any]]:
        """Sends a bid request to a custom HTTP/HTTPS bids endpoint if explicitly configured."""
        if not self.endpoint_url or not any(self.endpoint_url.endswith(s) for s in ["/api/v1/bids", "/v1/bids", "/bids"]):
            return []
        payload = {
            "query": query,
            "category": category,
            "ad_format": "a2ui_sponsored_card_v09",
            "limit": limit,
            "device": {"os": "web", "a2ui_version": "0.9"},
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Google-ADK-A2UI-Client/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            req = urllib.request.Request(
                self.endpoint_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    cards = data.get("cards") or data.get("bids") or []
                    if cards:
                        return cards
        except Exception:
            pass
        return []

    @staticmethod
    def _clean_commercial_search_query(query: str) -> str:
        """
        Generic cleaning of conversational query prefixes without hardcoding any product or domain words.
        """
        cleaned = re.sub(
            r"^(can\s+you\s+tell\s+me\s+(which\s+|what\s+)?|what\s+is\s+(a\s+|an\s+|the\s+)?|what\s+are\s+(the\s+)?|which\s+|explain\s+|how\s+to\s+(buy\s+|use\s+)?|compare\s+|best\s+|top\s+)",
            "",
            query.strip(),
            flags=re.IGNORECASE,
        ).strip()
        return cleaned.strip(" ?!.,") or query.strip()

    def _fetch_from_serpapi(
        self,
        query: str,
        entity_queries: Optional[list[str]] = None,
        limit: int = 3,
        category: str = "general",
        region: Optional[str] = None,
        location: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Queries SerpApi Google Paid Search Ads (engine=google_ads) and Google Shopping dynamically."""
        if not self.api_key:
            return []

        from google_a2a_agent.quota_manager import quota_manager
        serp_quota = quota_manager.get_serpapi_quota()
        if serp_quota.get("is_exhausted"):
            print("[SerpApi] Free quota complete. Skipping live ad call.")
            return []

        gl = region or os.getenv("SERPAPI_GL", "us")
        loc = location or os.getenv("SERPAPI_LOCATION", "New York, United States")
        hl = os.getenv("SERPAPI_HL", "en")

        # Determine target search terms from entity_queries or clean query
        candidate_queries: list[str] = []
        if entity_queries and isinstance(entity_queries, list):
            for eq in entity_queries:
                clean_eq = str(eq).strip()
                if clean_eq and clean_eq not in candidate_queries:
                    candidate_queries.append(clean_eq)

        clean_q = self._clean_commercial_search_query(query)
        if clean_q and clean_q not in candidate_queries:
            candidate_queries.append(clean_q)

        cards: list[dict[str, Any]] = []

        # 1. First priority: Genuine Paid Google Search Ads (engine=google_ads)
        for target_q in candidate_queries:
            if len(cards) >= limit:
                break
            print(f"[SerpApi] Requesting live Google Ads for target: '{target_q}' (gl={gl}, loc={loc}) ...")
            params = urllib.parse.urlencode({
                "engine": "google_ads",
                "q": target_q,
                "gl": gl,
                "hl": hl,
                "location": loc,
                "api_key": self.api_key,
            })
            url = f"{self.endpoint_url}?{params}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        ads = data.get("ads", [])
                        for idx, ad in enumerate(ads[: limit - len(cards)], len(cards) + 1):
                            title = ad.get("title", "")
                            link = ad.get("tracking_link") or ad.get("link", "")
                            domain = ad.get("displayed_link") or ad.get("source") or "Verified Sponsor"
                            clean_dom = re.sub(r"^https?://", "", str(domain)).split("/")[0].strip()
                            snippet = ad.get("description") or ad.get("snippet", "")
                            exts = ad.get("extensions") or []
                            badge = str(exts[0] if exts else "Sponsored")[:24]
                            logo_url = ad.get("thumbnail") or f"https://www.google.com/s2/favicons?domain={clean_dom}&sz=128"
                            if title and link:
                                cards.append({
                                    "campaign_id": f"serpapi_ad_{idx}",
                                    "sponsor_name": clean_dom or "Verified Sponsor",
                                    "category": category,
                                    "headline": title,
                                    "body": snippet or f"Sponsored offer from {clean_dom}",
                                    "cta_label": "Visit Site",
                                    "target_url": link if link.startswith("http") else f"https://{link}",
                                    "media_url": logo_url,
                                    "promo_code": f"SERP_{idx}",
                                    "badge": badge,
                                    "cpm_inr": 450.0,
                                    "clearing_price_inr": 420.0,
                                    "disclosure": "Sponsored",
                                })
            except Exception as e:
                print(f"[SerpApi] Google Ads error for '{target_q}': {e}")

        # 2. Second priority: If more cards are needed, query verified Google Shopping offers
        if len(cards) < limit:
            for target_q in candidate_queries:
                if len(cards) >= limit:
                    break
                remaining = limit - len(cards)
                print(f"[SerpApi] Requesting live Google Shopping for target: '{target_q}' (gl={gl}) ...")
                shop_params = urllib.parse.urlencode({
                    "engine": "google_shopping",
                    "q": target_q,
                    "gl": gl,
                    "hl": hl,
                    "api_key": self.api_key,
                })
                shop_url = f"{self.endpoint_url}?{shop_params}"
                try:
                    shop_req = urllib.request.Request(shop_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                    with urllib.request.urlopen(shop_req, timeout=self.timeout_seconds) as resp:
                        if resp.status == 200:
                            shop_data = json.loads(resp.read().decode("utf-8"))
                            items = shop_data.get("shopping_results", [])
                            for s_idx, it in enumerate(items[:remaining], len(cards) + 1):
                                title = it.get("title", "")
                                source = it.get("source", "Verified Merchant")
                                link = it.get("product_link") or it.get("link") or ""
                                if not link and it.get("serpapi_link"):
                                    link = f"https://www.google.com/search?q={urllib.parse.quote(title + ' ' + source)}"
                                price = it.get("price")
                                badge = str(price)[:24] if price else "In Stock"
                                rating = it.get("rating")
                                rating_str = f" • ★ {rating}" if rating else ""
                                thumbnail = it.get("thumbnail") or f"https://www.google.com/s2/favicons?domain=google.com&sz=128"
                                if title and link:
                                    body_text = f"Verified merchant: {source}."
                                    if price:
                                        body_text = f"Official price: {price}{rating_str}. Verified merchant: {source}."
                                    cards.append({
                                        "campaign_id": f"serpapi_shop_{s_idx}",
                                        "sponsor_name": source,
                                        "category": category,
                                        "headline": title,
                                        "body": body_text,
                                        "cta_label": "View Deal",
                                        "target_url": link if link.startswith("http") else f"https://{link}",
                                        "media_url": thumbnail,
                                        "promo_code": f"SHOP_{s_idx}",
                                        "badge": badge,
                                        "cpm_inr": 480.0,
                                        "clearing_price_inr": 440.0,
                                        "disclosure": "Sponsored",
                                    })
                except Exception as e:
                    print(f"[SerpApi] Google Shopping error for '{target_q}': {e}")

        print(f"[SerpApi] Result: Retrieved {len(cards)} live commercial cards.")
        return cards[:limit]

    def fetch_sponsored_cards(
        self,
        query: str,
        category: str = "general",
        entity_queries: Optional[list[str]] = None,
        limit: int = 3,
        region: Optional[str] = None,
        location: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        if not query or not query.strip():
            return []

        # Block casual greetings and explicitly non-commercial educational concepts
        clean_q = query.strip().lower()
        for pat in CASUAL_CHAT_PATTERNS + NON_COMMERCIAL_CONCEPT_PATTERNS:
            if re.search(pat, clean_q):
                return []

        # Custom HTTP bids endpoint if explicitly set (for tests / external DSP integration)
        if self.endpoint_url and any(self.endpoint_url.endswith(s) for s in ["/api/v1/bids", "/v1/bids", "/bids"]):
            res = self._fetch_from_http_endpoint(query, category=category, limit=limit)
            if res:
                return res
            return []

        # STRICT QUOTA SAFEGUARD: In automated tests, NEVER call SerpApi (quota strictly limited to manual testing)
        if os.getenv("TESTING") == "1" or "PYTEST_CURRENT_TEST" in os.environ or os.getenv("CI") == "true":
            return self.sandbox.execute_realtime_auction(search_query=query, top_k=limit, category=category)

        # Live SerpApi Google Ads & Google Shopping (manual user interaction)
        if self.api_key:
            cards = self._fetch_from_serpapi(
                query=query,
                entity_queries=entity_queries,
                limit=limit,
                category=category,
                region=region,
                location=location,
            )
            return cards

        return []

    def log_impressions(self, session_id: str, winning_campaigns: list[dict[str, Any]]) -> dict[str, Any]:
        if not winning_campaigns:
            return {}
        return self.sandbox.log_batch_impressions(session_id, winning_campaigns)

    def log_click(self, session_id: str, campaign_id: str) -> dict[str, Any]:
        return self.sandbox.log_click(session_id, campaign_id)

    def get_telemetry(self) -> dict[str, Any]:
        return self.sandbox.get_telemetry_summary()


RealHttpAdServerClient = RealSearchEngineAdClient


def get_ad_network_client() -> BaseAdNetworkClient:
    """Returns RealSearchEngineAdClient configured with .env credentials."""
    return RealSearchEngineAdClient()
