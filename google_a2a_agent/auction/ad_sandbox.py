import copy
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

DEFAULT_DB_PATH = Path(os.getenv("AD_TELEMETRY_DB_PATH", "ad_telemetry.db"))

# 1. Expanded Real-Time Programmatic Ad Inventory (Zero-Setup DSP Catalog)
MOCK_CAMPAIGNS: list[dict[str, Any]] = [
    # --- Category: GPU Compute & Cloud Infrastructure ---
    {
        "campaign_id": "camp_gpu_01",
        "sponsor_name": "TensorDock Cloud",
        "category": "gpu_compute",
        "keywords": ["gpu", "cloud", "kubernetes", "deepseek", "vllm", "h100", "serverless", "inference", "ollama"],
        "headline": "Deploy H100 & L40S GPUs at 60% Lower Cost",
        "body": "Instant bare-metal and Kubernetes GPU clusters with zero cold starts. Claim ₹5,000 in free ADK developer credits.",
        "cta_label": "Claim ₹5,000 Credit",
        "target_url": "https://tensordock.com/adk-promo",
        "media_url": "https://www.google.com/s2/favicons?domain=tensordock.com&sz=128",
        "promo_code": "ADK5000",
        "badge": "Lowest Cost/hr",
        "cpm_inr": 480.0,
        "cpc_inr": 42.0,
        "disclosure": "Sponsored",
    },
    {
        "campaign_id": "camp_gpu_02",
        "sponsor_name": "RunPod Serverless",
        "category": "gpu_compute",
        "keywords": ["serverless", "gpu", "pod", "container", "inference", "qwen", "mistral", "scale", "vllm"],
        "headline": "Serverless GPUs with 1-Second Cold Starts",
        "body": "Pay-per-second GPU workers with preloaded vLLM, HuggingFace weights, and instant global auto-scaling.",
        "cta_label": "Deploy Pod",
        "target_url": "https://www.runpod.io/adk",
        "media_url": "https://www.google.com/s2/favicons?domain=runpod.io&sz=128",
        "promo_code": "RUNPOD_ADK",
        "badge": "1s Cold Starts",
        "cpm_inr": 440.0,
        "cpc_inr": 38.0,
        "disclosure": "Sponsored",
    },
    {
        "campaign_id": "camp_gpu_03",
        "sponsor_name": "Lambda Cloud",
        "category": "gpu_compute",
        "keywords": ["cluster", "training", "h100", "infiniband", "fine-tuning", "lora", "nvidia", "quantum"],
        "headline": "NVIDIA Quantum InfiniBand GPU Clusters",
        "body": "Dedicated high-throughput GPU supercomputing designed for multi-agent LoRA fine-tuning and inference.",
        "cta_label": "Reserve Cluster",
        "target_url": "https://lambdalabs.com/adk",
        "media_url": "https://www.google.com/s2/favicons?domain=lambdalabs.com&sz=128",
        "promo_code": "LAMBDA_ADK",
        "badge": "InfiniBand 3.2Tb/s",
        "cpm_inr": 410.0,
        "cpc_inr": 36.0,
        "disclosure": "Sponsored",
    },
    # --- Category: Vector Databases & Agent Memory ---
    {
        "campaign_id": "camp_vectordb_01",
        "sponsor_name": "Qdrant Cloud",
        "category": "vector_db",
        "keywords": ["vector", "rag", "qdrant", "embedding", "search", "memory", "hybrid", "database", "retrieval"],
        "headline": "Sub-Millisecond Vector Search for Multi-Agent Memory",
        "body": "Scale to 100M+ vectors with zero-downtime quantization and rich payload filtering. Start with 4GB free.",
        "cta_label": "Provision Free Cluster",
        "target_url": "https://qdrant.tech/free-tier",
        "media_url": "https://www.google.com/s2/favicons?domain=qdrant.tech&sz=128",
        "promo_code": "QDRANT_A2UI",
        "badge": "Sub-Millisecond",
        "cpm_inr": 390.0,
        "cpc_inr": 35.0,
        "disclosure": "Sponsored",
    },
    {
        "campaign_id": "camp_vectordb_02",
        "sponsor_name": "Pinecone Serverless",
        "category": "vector_db",
        "keywords": ["pinecone", "serverless", "vector", "index", "retrieval", "semantic", "agent", "memory"],
        "headline": "Serverless Vector Indexing with Zero Ops",
        "body": "Separate storage and compute for true cost elasticity. Fast hybrid sparse/dense search for agent pipelines.",
        "cta_label": "Launch Index",
        "target_url": "https://www.pinecone.io/adk",
        "media_url": "https://www.google.com/s2/favicons?domain=pinecone.io&sz=128",
        "promo_code": "PINECONE_A2UI",
        "badge": "Serverless Ops",
        "cpm_inr": 360.0,
        "cpc_inr": 32.0,
        "disclosure": "Sponsored",
    },
    {
        "campaign_id": "camp_vectordb_03",
        "sponsor_name": "Weaviate Cloud",
        "category": "vector_db",
        "keywords": ["weaviate", "graphql", "rag", "multimodal", "vector", "database", "knowledge", "hybrid"],
        "headline": "Multimodal Vector Database & Graph RAG",
        "body": "Native vector + hybrid keyword search with built-in Cross-Encoders and multi-tenant isolation.",
        "cta_label": "Try Cloud Sandbox",
        "target_url": "https://weaviate.io/sandbox",
        "media_url": "https://www.google.com/s2/favicons?domain=weaviate.io&sz=128",
        "promo_code": "WEAVIATE_A2UI",
        "badge": "Graph RAG",
        "cpm_inr": 330.0,
        "cpc_inr": 30.0,
        "disclosure": "Sponsored",
    },
    # --- Category: LLM Observability & Evaluation ---
    {
        "campaign_id": "camp_observability_01",
        "sponsor_name": "Arize Phoenix",
        "category": "observability",
        "keywords": ["eval", "test", "benchmark", "drift", "trace", "telemetry", "monitor", "opentelemetry", "phoenix"],
        "headline": "Open-Source LLM Tracing & Behavioral Drift Evaluation",
        "body": "Zero-config OpenTelemetry tracing for Google ADK and LiteLLM workflows. Diagnose latency and halluncinations.",
        "cta_label": "Launch Sandbox",
        "target_url": "https://phoenix.arize.com/adk",
        "media_url": "https://www.google.com/s2/favicons?domain=arize.com&sz=128",
        "promo_code": "PHOENIX_OSS",
        "badge": "Open-Source OTel",
        "cpm_inr": 320.0,
        "cpc_inr": 28.0,
        "disclosure": "Sponsored",
    },
    {
        "campaign_id": "camp_observability_02",
        "sponsor_name": "Langfuse",
        "category": "observability",
        "keywords": ["langfuse", "tracing", "prompt", "cost", "tokens", "metrics", "monitor", "latency"],
        "headline": "Open-Source LLM Engineering Platform",
        "body": "Track prompt latency, token costs, and user feedback across multi-agent pipelines with instant SDK setup.",
        "cta_label": "Start Free Cloud",
        "target_url": "https://langfuse.com/adk",
        "media_url": "https://www.google.com/s2/favicons?domain=langfuse.com&sz=128",
        "promo_code": "LANGFUSE_A2UI",
        "badge": "Cost Analytics",
        "cpm_inr": 300.0,
        "cpc_inr": 26.0,
        "disclosure": "Sponsored",
    },
    # --- Backwards compatibility anchor ---
    {
        "campaign_id": "camp_adk_01",
        "sponsor_name": "CloudScale GPU",
        "category": "gpu_compute",
        "keywords": ["cloudscale", "gpu", "inference", "free", "credits", "70b"],
        "headline": "Run 70B Open-Source Models with Zero Cold Starts",
        "body": "Claim ₹10,000 in free inference credits for your Google ADK agents.",
        "cta_label": "Claim Free Credits",
        "target_url": "https://tensordock.com/cloudscale-offer",
        "media_url": "https://www.google.com/s2/favicons?domain=tensordock.com&sz=128",
        "promo_code": "CLOUDSCALE10K",
        "badge": "₹10,000 Free",
        "cpm_inr": 500.0,
        "cpc_inr": 50.0,
        "disclosure": "Sponsored",
    },
    # --- Category: Travel, Flights & Hospitality ---
    {
        "campaign_id": "camp_travel_01",
        "sponsor_name": "Skyscanner",
        "category": "travel_hospitality",
        "keywords": ["flight", "flights", "travel", "airline", "tickets", "cheap", "booking", "skyscanner", "vacation"],
        "headline": "Compare & Book Cheap Flights Worldwide with Zero Fees",
        "body": "Find the cheapest flights across 1,200+ airlines. Set price alerts and save up to 40% on round trips.",
        "cta_label": "Search Flights",
        "target_url": "https://www.skyscanner.com/adk-deals",
        "media_url": "https://www.google.com/s2/favicons?domain=skyscanner.com&sz=128",
        "promo_code": "FLIGHT40",
        "badge": "Save up to 40%",
        "cpm_inr": 420.0,
        "cpc_inr": 35.0,
        "disclosure": "Sponsored",
    },
    {
        "campaign_id": "camp_travel_02",
        "sponsor_name": "Booking.com",
        "category": "travel_hospitality",
        "keywords": ["hotel", "hotels", "stay", "resort", "booking", "rooms", "accommodation", "travel", "vacation"],
        "headline": "Hotels, Homes & Vacation Stays with Free Cancellation",
        "body": "Book verified accommodations in over 220 countries with price match guarantee and flexible cancellation.",
        "cta_label": "View Hotels",
        "target_url": "https://www.booking.com/adk-promo",
        "media_url": "https://www.google.com/s2/favicons?domain=booking.com&sz=128",
        "promo_code": "STAYEASY",
        "badge": "Free Cancellation",
        "cpm_inr": 380.0,
        "cpc_inr": 32.0,
        "disclosure": "Sponsored",
    },
    {
        "campaign_id": "camp_travel_03",
        "sponsor_name": "Emirates Airlines",
        "category": "travel_hospitality",
        "keywords": ["airline", "flight", "emirates", "international", "dubai", "london", "tokyo", "luxury", "tickets"],
        "headline": "Fly Better to Over 140 Destinations Across 6 Continents",
        "body": "Experience world-class service, gourmet dining, and award-winning in-flight entertainment on Emirates.",
        "cta_label": "Book Flight",
        "target_url": "https://www.emirates.com/offers",
        "media_url": "https://www.google.com/s2/favicons?domain=emirates.com&sz=128",
        "promo_code": "EMIRATES_A2UI",
        "badge": "World-Class",
        "cpm_inr": 460.0,
        "cpc_inr": 40.0,
        "disclosure": "Sponsored",
    },
    # --- Category: Finance & Insurance ---
    {
        "campaign_id": "camp_finance_01",
        "sponsor_name": "GEICO Insurance",
        "category": "financial_insurance",
        "keywords": ["insurance", "car", "auto", "policy", "quote", "coverage", "vehicle", "geico", "rates"],
        "headline": "15 Minutes Could Save You 15% or More on Car Insurance",
        "body": "Fast, free online car insurance quotes with 24/7 support and nationwide coverage discounts.",
        "cta_label": "Get Free Quote",
        "target_url": "https://www.geico.com/auto-quotes",
        "media_url": "https://www.google.com/s2/favicons?domain=geico.com&sz=128",
        "promo_code": "SAVE15",
        "badge": "Save 15%+",
        "cpm_inr": 490.0,
        "cpc_inr": 45.0,
        "disclosure": "Sponsored",
    },
    {
        "campaign_id": "camp_finance_02",
        "sponsor_name": "Progressive Insurance",
        "category": "financial_insurance",
        "keywords": ["insurance", "progressive", "auto", "home", "rates", "coverage", "bundle", "save"],
        "headline": "Bundle Auto & Home Insurance to Save An Average of ₹6,000",
        "body": "Compare personalized rate quotes with the Name Your Price tool and customized bundle savings.",
        "cta_label": "Explore Rates",
        "target_url": "https://www.progressive.com/bundle",
        "media_url": "https://www.google.com/s2/favicons?domain=progressive.com&sz=128",
        "promo_code": "BUNDLE_SAVE",
        "badge": "Bundle & Save",
        "cpm_inr": 450.0,
        "cpc_inr": 41.0,
        "disclosure": "Sponsored",
    },
    {
        "campaign_id": "camp_finance_03",
        "sponsor_name": "Stripe Atlas",
        "category": "financial_insurance",
        "keywords": ["incorporation", "startup", "legal", "stripe", "atlas", "company", "bank", "delaware", "business"],
        "headline": "Form a Delaware C-Corp or LLC in Days from Anywhere",
        "body": "Everything you need to incorporate your global startup, issue stock, and open a business bank account.",
        "cta_label": "Start Incorporation",
        "target_url": "https://stripe.com/atlas/adk",
        "media_url": "https://www.google.com/s2/favicons?domain=stripe.com&sz=128",
        "promo_code": "ATLAS_START",
        "badge": "Delaware C-Corp",
        "cpm_inr": 470.0,
        "cpc_inr": 44.0,
        "disclosure": "Sponsored",
    },
    # --- Category: SaaS & Business Tools ---
    {
        "campaign_id": "camp_saas_01",
        "sponsor_name": "HubSpot CRM",
        "category": "saas_software",
        "keywords": ["crm", "sales", "leads", "hubspot", "marketing", "pipeline", "contacts", "software", "startup"],
        "headline": "Free CRM Platform with Unlimited Users & Contacts",
        "body": "Align your sales, marketing, and customer service on an all-in-one AI-powered customer platform.",
        "cta_label": "Get Free CRM",
        "target_url": "https://www.hubspot.com/crm-free",
        "media_url": "https://www.google.com/s2/favicons?domain=hubspot.com&sz=128",
        "promo_code": "HUBSPOT_FREE",
        "badge": "100% Free Forever",
        "cpm_inr": 480.0,
        "cpc_inr": 43.0,
        "disclosure": "Sponsored",
    },
    {
        "campaign_id": "camp_saas_02",
        "sponsor_name": "Monday.com",
        "category": "saas_software",
        "keywords": ["project", "management", "workflow", "team", "tasks", "monday", "kanban", "collaboration"],
        "headline": "Visual Work Management Platform for High-Velocity Teams",
        "body": "Automate routine tasks, track roadmaps, and collaborate in real time with 200+ pre-built templates.",
        "cta_label": "Start Free Trial",
        "target_url": "https://monday.com/trial",
        "media_url": "https://www.google.com/s2/favicons?domain=monday.com&sz=128",
        "promo_code": "MONDAY_A2UI",
        "badge": "14-Day Free Trial",
        "cpm_inr": 410.0,
        "cpc_inr": 37.0,
        "disclosure": "Sponsored",
    },
    {
        "campaign_id": "camp_saas_03",
        "sponsor_name": "Linear",
        "category": "saas_software",
        "keywords": ["linear", "issue", "tracking", "bugs", "sprint", "roadmap", "developer", "engineering"],
        "headline": "Linear — The Purpose-Built Issue Tracker for High-Performing Teams",
        "body": "Streamline issues, sprints, and product roadmaps with keyboard-first speed and Git integrations.",
        "cta_label": "Try Linear Free",
        "target_url": "https://linear.app/adk",
        "media_url": "https://www.google.com/s2/favicons?domain=linear.app&sz=128",
        "promo_code": "LINEAR_A2UI",
        "badge": "Keyboard-First",
        "cpm_inr": 430.0,
        "cpc_inr": 39.0,
        "disclosure": "Sponsored",
    },
    # --- Category: Education, Courses & Careers ---
    {
        "campaign_id": "camp_edu_01",
        "sponsor_name": "Coursera Plus",
        "category": "education_careers",
        "keywords": ["course", "courses", "learn", "coursera", "degree", "certificate", "python", "data", "ai", "bootcamp", "training"],
        "headline": "Unlimited Access to 7,000+ Courses & Professional Certificates",
        "body": "Learn in-demand skills from Google, IBM, Stanford, and Meta. Earn accredited professional certificates.",
        "cta_label": "Start 7-Day Trial",
        "target_url": "https://www.coursera.org/plus-trial",
        "media_url": "https://www.google.com/s2/favicons?domain=coursera.org&sz=128",
        "promo_code": "COURSERA_LEARN",
        "badge": "Top University Certs",
        "cpm_inr": 430.0,
        "cpc_inr": 38.0,
        "disclosure": "Sponsored",
    },
    {
        "campaign_id": "camp_edu_02",
        "sponsor_name": "DataCamp",
        "category": "education_careers",
        "keywords": ["datacamp", "python", "sql", "data", "science", "coding", "machine", "learning", "exercises"],
        "headline": "Learn Python, SQL & AI from Scratch with Interactive Practice",
        "body": "Build real data science and AI skills in short, hands-on lessons with zero environment setup required.",
        "cta_label": "Start Learning Free",
        "target_url": "https://www.datacamp.com/start",
        "media_url": "https://www.google.com/s2/favicons?domain=datacamp.com&sz=128",
        "promo_code": "DATACAMP_FREE",
        "badge": "Interactive Code",
        "cpm_inr": 390.0,
        "cpc_inr": 34.0,
        "disclosure": "Sponsored",
    },
    # --- Category: Consumer Hardware & Gear ---
    {
        "campaign_id": "camp_prod_01",
        "sponsor_name": "Apple",
        "category": "consumer_products",
        "keywords": ["laptop", "macbook", "apple", "m3", "m4", "computer", "pro", "coding", "developer"],
        "headline": "MacBook Pro 14-inch with M3 Pro — Built for Pro Developers",
        "body": "Up to 22 hours of battery life and extreme performance for compiling, AI inference, and creative workflows.",
        "cta_label": "View Specs & Buy",
        "target_url": "https://www.apple.com/macbook-pro",
        "media_url": "https://www.google.com/s2/favicons?domain=apple.com&sz=128",
        "promo_code": "APPLE_DEV",
        "badge": "Pro Performance",
        "cpm_inr": 490.0,
        "cpc_inr": 46.0,
        "disclosure": "Sponsored",
    },
    {
        "campaign_id": "camp_prod_02",
        "sponsor_name": "Asus",
        "category": "consumer_products",
        "keywords": ["asus", "zenbook", "laptop", "oled", "dual", "screen", "portable", "ultrabook", "best"],
        "headline": "ASUS Zenbook Duo Dual-Screen OLED Laptop",
        "body": "Twin full-size 3K 120Hz OLED touchscreens with detachable Bluetooth keyboard for maximum multitasking.",
        "cta_label": "Order Now",
        "target_url": "https://www.asus.com/zenbook-duo",
        "media_url": "https://www.google.com/s2/favicons?domain=asus.com&sz=128",
        "promo_code": "ZENBOOK_A2UI",
        "badge": "Dual 3K OLED",
        "cpm_inr": 450.0,
        "cpc_inr": 41.0,
        "disclosure": "Sponsored",
    },
    {
        "campaign_id": "camp_prod_03",
        "sponsor_name": "Nike Running",
        "category": "consumer_products",
        "keywords": ["shoes", "shoe", "nike", "running", "sneakers", "marathon", "footwear", "air", "max"],
        "headline": "Nike Pegasus 41 Road Running Shoes with ReactX Foam",
        "body": "Responsive cushioning and breathable engineered mesh designed for daily road running and marathons.",
        "cta_label": "Shop Nike Pegasus",
        "target_url": "https://www.nike.com/pegasus-41",
        "media_url": "https://www.google.com/s2/favicons?domain=nike.com&sz=128",
        "promo_code": "NIKE_PEGASUS",
        "badge": "Top Rated",
        "cpm_inr": 440.0,
        "cpc_inr": 39.0,
        "disclosure": "Sponsored",
    },
]


class LocalAdExchangeSandbox:
    """
    Self-contained ad auction, real-time second-price bidding engine, and telemetry tracker
    backed by local SQLite. Supports single-banner and 3-card real-time search auctions.
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ad_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    session_id TEXT,
                    campaign_id TEXT,
                    sponsor_name TEXT,
                    event_type TEXT,  -- 'IMPRESSION' or 'CLICK'
                    revenue_inr REAL,
                    llm_tokens_used INTEGER,
                    llm_cost_inr REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS query_ad_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    session_id TEXT,
                    query_text TEXT,
                    intent_category TEXT,
                    is_commercial INTEGER,
                    ads_count INTEGER,
                    ads_summary TEXT,  -- JSON string of [{sponsor_name, headline, price, target_url}]
                    clearing_price_inr REAL,
                    llm_tokens_used INTEGER,
                    llm_cost_inr REAL,
                    revenue_inr REAL
                )
                """
            )

    def clear_events(self) -> None:
        """Clears all logged telemetry events and query audits for hermetic testing."""
        with self._connection() as conn:
            conn.execute("DELETE FROM ad_events")
            conn.execute("DELETE FROM query_ad_audit")
            conn.commit()
            conn.execute("VACUUM")

    @staticmethod
    def personalize_copy(campaign: dict[str, Any], query_text: str) -> dict[str, Any]:
        """
        Dynamically adapts promotional copy in real time based on search query intent.
        """
        camp = copy.deepcopy(campaign)
        q = (query_text or "").lower()

        if "deepseek" in q and ("gpu" in camp.get("category", "") or "cloud" in camp["sponsor_name"].lower()):
            camp["headline"] = f"Deploy DeepSeek-R1 at 60% Lower Cost on {camp['sponsor_name']}"
            camp["body"] = "Zero cold-start vLLM nodes optimized for DeepSeek reasoning. Claim free developer credits."
            camp["badge"] = "DeepSeek Optimized"
        elif "qwen" in q and ("gpu" in camp.get("category", "") or "cloud" in camp["sponsor_name"].lower()):
            camp["headline"] = f"Host Qwen-2.5-Coder with Instant vLLM Scaling on {camp['sponsor_name']}"
            camp["badge"] = "Qwen Verified"
        elif "kubernetes" in q and "gpu" in camp.get("category", ""):
            camp["headline"] = f"Automated Kubernetes GPU Clusters on {camp['sponsor_name']}"
            camp["badge"] = "K8s Ready"
        elif ("memory" in q or "retrieval" in q) and "vector" in camp.get("category", ""):
            camp["headline"] = f"Sub-Millisecond Multi-Agent Memory on {camp['sponsor_name']}"
            camp["badge"] = "Agent Memory"
        elif ("drift" in q or "hallucination" in q) and "eval" in camp.get("category", ""):
            camp["headline"] = f"Detect LLM Drift & Hallucinations with {camp['sponsor_name']}"
            camp["badge"] = "Drift Detection"

        return camp

    def match_campaign(self, query_text: str = "") -> dict[str, Any]:
        """Single top-1 campaign matcher for backward compatibility."""
        top_k = self.execute_realtime_auction(query_text, top_k=1)
        return top_k[0] if top_k else MOCK_CAMPAIGNS[0]

    def execute_realtime_auction(self, search_query: str = "", top_k: int = 3, category: str = "") -> list[dict[str, Any]]:
        """
        Executes a real-time programmatic second-price auction (Vickrey Auction) across DSP inventory.
        1. Scores all campaigns by relevance = hits * 10.0 + category_match_bonus.
        2. Strictly prioritizes category-aligned sponsors over unrelated categories.
        3. Selects top_k winning campaigns.
        4. Sets clearing price = next competitor bid + 1.0 (capped at winner's max bid).
        5. Contextually personalizes headline and badge in real time.
        """
        query_lower = (search_query or "").lower()
        scored = []
        for camp in MOCK_CAMPAIGNS:
            hits = sum(1 for kw in camp["keywords"] if kw in query_lower)
            camp_cat = camp.get("category", "")
            cat_bonus = 50.0 if (category and camp_cat == category) else 0.0
            relevance = (hits * 10.0) + cat_bonus
            if relevance > 0:
                score = relevance * float(camp.get("cpm_inr", 300.0))
            else:
                score = float(camp.get("cpm_inr", 300.0)) * 0.01

            scored.append((score, camp))

        scored.sort(key=lambda x: x[0], reverse=True)
        winners = [item[1] for item in scored[:top_k]]

        results = []
        for i in range(len(winners)):
            winner = winners[i]
            # Second-price clearing price: competitor bid + ₹1.00
            if i + 1 < len(scored):
                clearing_price = float(scored[i + 1][1].get("cpm_inr", 250.0)) + 1.0
            else:
                clearing_price = float(winner.get("cpm_inr", 300.0)) * 0.85

            clearing_price = min(clearing_price, float(winner.get("cpm_inr", 300.0)))
            clearing_price = round(clearing_price, 2)

            personalized = self.personalize_copy(winner, search_query)
            personalized["clearing_price_inr"] = clearing_price
            results.append(personalized)

        return results

    run_second_price_auction = execute_realtime_auction

    def log_impression(
        self,
        session_id: str,
        campaign: dict[str, Any],
        total_tokens: int = 0,
    ) -> dict[str, Any]:
        """Logs a single AdBanner render impression."""
        cpm = float(campaign.get("clearing_price_inr", campaign.get("cpm_inr", 450.0)))
        impression_rev_inr = cpm / 1000.0
        llm_cost_inr = (float(total_tokens) / 1000.0) * 0.025

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO ad_events
                (timestamp, session_id, campaign_id, sponsor_name, event_type, revenue_inr, llm_tokens_used, llm_cost_inr)
                VALUES (?, ?, ?, ?, 'IMPRESSION', ?, ?, ?)
                """,
                (
                    time.time(),
                    str(session_id),
                    campaign.get("campaign_id", "unknown"),
                    campaign.get("sponsor_name", "Unknown Sponsor"),
                    impression_rev_inr,
                    total_tokens,
                    llm_cost_inr,
                ),
            )
        return self.get_telemetry_summary()

    def log_batch_impressions(
        self,
        session_id: str,
        winning_campaigns: list[dict[str, Any]],
        total_tokens: int = 0,
    ) -> dict[str, Any]:
        """
        Logs real-time 3-card batch impressions to SQLite.
        LLM inference token cost is attributed once to the search turn.
        """
        llm_cost_inr = (float(total_tokens) / 1000.0) * 0.025
        with self._connection() as conn:
            for idx, camp in enumerate(winning_campaigns):
                clearing_price = float(camp.get("clearing_price_inr", camp.get("cpm_inr", 350.0)))
                imp_rev_inr = clearing_price / 1000.0
                cost_attr = llm_cost_inr if idx == 0 else 0.0

                conn.execute(
                    """
                    INSERT INTO ad_events
                    (timestamp, session_id, campaign_id, sponsor_name, event_type, revenue_inr, llm_tokens_used, llm_cost_inr)
                    VALUES (?, ?, ?, ?, 'IMPRESSION', ?, ?, ?)
                    """,
                    (
                        time.time(),
                        str(session_id),
                        camp.get("campaign_id", "unknown"),
                        camp.get("sponsor_name", "Unknown Sponsor"),
                        imp_rev_inr,
                        total_tokens if idx == 0 else 0,
                        cost_attr,
                    ),
                )
        return self.get_telemetry_summary()

    def log_click(self, session_id: str, campaign_id: str) -> dict[str, Any]:
        """Logs a user/simulator clicking a SponsoredCard or AdBanner CTA button."""
        campaign = next(
            (c for c in MOCK_CAMPAIGNS if c["campaign_id"] == campaign_id),
            MOCK_CAMPAIGNS[0],
        )
        click_rev_inr = float(campaign.get("cpc_inr", 42.0))

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO ad_events
                (timestamp, session_id, campaign_id, sponsor_name, event_type, revenue_inr, llm_tokens_used, llm_cost_inr)
                VALUES (?, ?, ?, ?, 'CLICK', ?, 0, 0.0)
                """,
                (
                    time.time(),
                    str(session_id),
                    campaign["campaign_id"],
                    campaign["sponsor_name"],
                    click_rev_inr,
                ),
            )
        return self.get_telemetry_summary()

    def log_query_audit(
        self,
        session_id: str,
        query_text: str,
        intent_category: str,
        is_commercial: bool,
        winning_cards: list[dict[str, Any]],
        total_tokens: int = 0,
    ) -> None:
        """Persists every search query, detected intent, and exact triggered ads for the dashboard."""
        ads_summary_list = []
        total_rev = 0.0
        clearing_price = 0.0
        for card in winning_cards:
            c_price = float(card.get("clearing_price_inr", card.get("cpm_inr", 350.0)))
            clearing_price = max(clearing_price, c_price)
            total_rev += c_price / 1000.0
            ads_summary_list.append({
                "sponsor_name": card.get("sponsor_name", "Unknown Sponsor"),
                "headline": card.get("headline", ""),
                "badge": str(card.get("badge", "")),
                "target_url": card.get("target_url", ""),
                "clearing_price_inr": c_price,
                "campaign_id": card.get("campaign_id", ""),
            })

        llm_cost_inr = (float(total_tokens) / 1000.0) * 0.025
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO query_ad_audit
                (timestamp, session_id, query_text, intent_category, is_commercial, ads_count, ads_summary, clearing_price_inr, llm_tokens_used, llm_cost_inr, revenue_inr)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    str(session_id),
                    query_text,
                    intent_category,
                    1 if is_commercial else 0,
                    len(winning_cards),
                    json.dumps(ads_summary_list),
                    clearing_price,
                    total_tokens,
                    llm_cost_inr,
                    total_rev,
                ),
            )

    def get_query_audits(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieves the recent query-to-ad audit log table for the analytics dashboard."""
        with self._connection() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM query_ad_audit ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
            audits = []
            for r in rows:
                audits.append({
                    "id": r["id"],
                    "timestamp": r["timestamp"],
                    "session_id": r["session_id"],
                    "query_text": r["query_text"],
                    "intent_category": r["intent_category"],
                    "is_commercial": bool(r["is_commercial"]),
                    "ads_count": r["ads_count"],
                    "ads_summary": json.loads(r["ads_summary"] or "[]"),
                    "clearing_price_inr": r["clearing_price_inr"],
                    "llm_tokens_used": r["llm_tokens_used"],
                    "llm_cost_inr": r["llm_cost_inr"],
                    "revenue_inr": r["revenue_inr"],
                })
            return audits

    def get_telemetry_summary(self) -> dict[str, Any]:
        """Aggregates live metrics for the ADK Web State Inspector & Dashboard."""
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM ad_events WHERE event_type = 'IMPRESSION'")
            impressions = cur.fetchone()[0] or 0

            cur.execute("SELECT COUNT(*) FROM ad_events WHERE event_type = 'CLICK'")
            clicks = cur.fetchone()[0] or 0

            cur.execute("SELECT COUNT(*) FROM query_ad_audit")
            total_queries = cur.fetchone()[0] or 0

            cur.execute(
                """
                SELECT
                    COALESCE(SUM(revenue_inr), 0.0),
                    COALESCE(SUM(llm_cost_inr), 0.0),
                    COALESCE(SUM(llm_tokens_used), 0)
                FROM ad_events
                """
            )
            total_rev, total_cost, total_tokens = cur.fetchone()

        ctr_pct = round((clicks / impressions * 100.0), 2) if impressions > 0 else 0.0
        net_profit_inr = round(total_rev - total_cost, 4)
        cost_recovery_pct = (
            round((total_rev / total_cost * 100.0), 1) if total_cost > 0 else 100.0
        )

        return {
            "total_queries": total_queries,
            "total_impressions": impressions,
            "total_clicks": clicks,
            "ctr_percent": f"{ctr_pct}%",
            "gross_ad_revenue_inr": f"₹{total_rev:.2f}",
            "llm_inference_cost_inr": f"₹{total_cost:.4f}",
            "net_margin_inr": f"₹{net_profit_inr:.2f}",
            "inference_cost_subsidized": f"{cost_recovery_pct}%",
            "total_tokens_processed": total_tokens,
            "recent_audits": self.get_query_audits(limit=25),
        }
