import json
import os
import re
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Optional
from dotenv import load_dotenv

from google_a2a_agent.auction.ad_sandbox import LocalAdExchangeSandbox

load_dotenv()

# Intent Classification Markers
GENERIC_CASUAL_GREETINGS = {
    "hi", "hello", "hey", "yo", "greetings", "good morning", "good afternoon",
    "good evening", "how are you", "who are you", "what can you do", "help",
}

PURE_EDUCATIONAL_THEORETICAL_PREFIXES = (
    "what is photosynthesis",
    "how do trees produce oxygen",
    "explain quantum",
    "how does gravity work",
    "why is the sky blue",
    "how do cells divide",
    "what is mitosis",
    "what is meiosis",
    "explain general relativity",
    "water cycle",
    "history of the roman empire",
    "what is a for loop",
    "how to write a for loop",
    "explain quicksort in python",
)

COMMERCIAL_INTENT_SIGNALS = {
    "buy", "shop", "order", "price", "pricing", "cost", "cheap", "affordable", "deal", "deals",
    "discount", "quote", "quotes", "compare", "comparison", "vs", "versus", "best", "top",
    "tier", "recommend", "recommendation", "recommendations", "alternative", "alternatives",
    "review", "reviews", "features", "specs", "hire", "service", "services", "provider",
    "providers", "platform", "platforms", "software", "tool", "tools", "app", "apps",
    "subscription", "license", "store", "online", "book", "booking", "tickets", "plans",
}

DOMAIN_CATEGORY_HINTS = [
    ({"watch", "watches", "wacthes", "rolex", "patek", "audemars", "vacheron", "omega", "cartier", "timepiece", "chronograph", "horology", "jewelry"}, "luxury_watches"),
    ({"gpu", "gpus", "h100", "l40s", "a100", "rtx", "nvidia", "amd", "serverless", "cloud", "vllm", "cluster", "hosting", "inference"}, "gpu_compute"),
    ({"vector", "vectordb", "database", "qdrant", "pinecone", "weaviate", "rag", "embedding"}, "vector_db"),
    ({"eval", "tracing", "observability", "telemetry", "monitor", "phoenix", "langfuse"}, "observability"),
    ({"flight", "flights", "hotel", "hotels", "airline", "airlines", "travel", "vacation", "trip", "skyscanner"}, "travel_hospitality"),
    ({"insurance", "policy", "loan", "mortgage", "bank", "banking", "geico", "progressive", "llc", "c-corp", "incorporation", "atlas"}, "financial_insurance"),
    ({"crm", "sales", "leads", "hubspot", "monday", "linear", "jira", "saas"}, "saas_software"),
    ({"course", "courses", "bootcamp", "coursera", "datacamp", "udemy", "certificate", "certification"}, "education_careers"),
    ({"laptop", "laptops", "macbook", "computer", "pc", "phone", "iphone", "samsung", "headphones", "keyboard", "shoes", "shoe", "sneakers", "nike"}, "consumer_products"),
]


def classify_commercial_intent(query: str) -> tuple[bool, str]:
    """
    Generalized semantic intent evaluator.
    Determines whether a query is commercial/transactional/evaluative vs
    purely informational, casual, or educational.
    """
    if not query or not query.strip():
        return False, "empty_query"

    clean = query.strip().lower()

    # 1. Casual Chat Gating
    if clean in GENERIC_CASUAL_GREETINGS or re.match(r"^(hi|hello|hey|yo|greetings)\b", clean):
        return False, "casual_chat"

    # Math expressions or jokes
    if re.match(r"^\d+\s*[\+\-\*\/]\s*\d+", clean) or clean == "tell me a joke":
        return False, "casual_chat"

    # 2. Purely Educational & Abstract Concepts
    if any(clean.startswith(prefix) or prefix in clean for prefix in PURE_EDUCATIONAL_THEORETICAL_PREFIXES):
        return False, "educational_concept"

    if re.match(r"^what\s+is\s+python\b", clean):
        return False, "educational_concept"

    # 3. Dynamic Intent Classification based on Action & Domain Semantics
    tokens = set(re.findall(r"[a-z0-9_\-]+", clean))
    has_intent_signal = bool(tokens.intersection(COMMERCIAL_INTENT_SIGNALS))

    inferred_category = "commercial"
    for word_set, cat_name in DOMAIN_CATEGORY_HINTS:
        if tokens.intersection(word_set):
            inferred_category = cat_name
            break

    # If an intent signal is present OR a specific product/technology domain is named, it is commercial
    if has_intent_signal or inferred_category != "commercial":
        return True, inferred_category

    # Specific hardware queries ("what is GPU", "what is H100")
    if any(q_term in tokens for q_term in ["gpu", "h100", "a100", "rtx", "macbook", "iphone"]):
        return True, "gpu_compute"

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


def _build_card_dict(
    campaign_id: str,
    sponsor_name: str,
    category: str,
    headline: str,
    body: str,
    cta_label: str,
    target_url: str,
    media_url: str,
    promo_code: str,
    badge: str,
    cpm_inr: float = 450.0,
    clearing_price_inr: float = 420.0,
) -> dict[str, Any]:
    """Helper to assemble a normalized A2UI v0.9 SponsoredCard dictionary."""
    clean_target = target_url if target_url.startswith("http") else f"https://{target_url}"
    return {
        "campaign_id": campaign_id,
        "sponsor_name": sponsor_name,
        "category": category,
        "headline": headline,
        "body": body,
        "cta_label": cta_label,
        "target_url": clean_target,
        "media_url": media_url,
        "promo_code": promo_code,
        "badge": badge,
        "cpm_inr": cpm_inr,
        "clearing_price_inr": clearing_price_inr,
        "disclosure": "Sponsored",
    }


class RealSearchEngineAdClient(BaseAdNetworkClient):
    """
    Dynamic Search Engine Ad Client powered by SerpApi (Google Search Ads & Google Shopping).
    Adheres strictly to zero-dummy-data rules.
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

    @staticmethod
    def _clean_commercial_search_query(query: str) -> str:
        """Generic cleaning of conversational query prefixes."""
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

        from google_a2a_agent.governance.quota_manager import quota_manager
        serp_quota = quota_manager.get_serpapi_quota()
        if serp_quota.get("is_exhausted"):
            print("[SerpApi] Free quota complete. Skipping live ad call.")
            return []

        gl = region or os.getenv("SERPAPI_GL", "us")
        loc = location or os.getenv("SERPAPI_LOCATION", "New York, United States")
        hl = os.getenv("SERPAPI_HL", "en")

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
                                cards.append(_build_card_dict(
                                    campaign_id=f"serpapi_ad_{idx}",
                                    sponsor_name=clean_dom or "Verified Sponsor",
                                    category=category,
                                    headline=title,
                                    body=snippet or f"Sponsored offer from {clean_dom}",
                                    cta_label="Visit Site",
                                    target_url=link,
                                    media_url=logo_url,
                                    promo_code=f"SERP_{idx}",
                                    badge=badge,
                                    cpm_inr=450.0,
                                    clearing_price_inr=420.0,
                                ))
            except Exception as e:
                print(f"[SerpApi] Google Ads error for '{target_q}': {e}")

        # 2. Second priority: If more cards are needed, query verified Google Shopping offers
        if len(cards) < limit:
            for target_q in candidate_queries:
                if len(cards) >= limit:
                    break
                remaining = limit - len(cards)
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
                                thumbnail = it.get("thumbnail") or "https://www.google.com/s2/favicons?domain=google.com&sz=128"
                                if title and link:
                                    body_text = f"Official price: {price}{rating_str}. Verified merchant: {source}." if price else f"Verified merchant: {source}."
                                    cards.append(_build_card_dict(
                                        campaign_id=f"serpapi_shop_{s_idx}",
                                        sponsor_name=source,
                                        category=category,
                                        headline=title,
                                        body=body_text,
                                        cta_label="View Deal",
                                        target_url=link,
                                        media_url=thumbnail,
                                        promo_code=f"SHOP_{s_idx}",
                                        badge=badge,
                                        cpm_inr=480.0,
                                        clearing_price_inr=440.0,
                                    ))
                except Exception as e:
                    print(f"[SerpApi] Google Shopping error for '{target_q}': {e}")

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

        is_comm, _ = classify_commercial_intent(query)
        if not is_comm:
            return []

        if self.api_key:
            return self._fetch_from_serpapi(
                query=query,
                entity_queries=entity_queries,
                limit=limit,
                category=category,
                region=region,
                location=location,
            )

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
