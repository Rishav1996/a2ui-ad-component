import json
import os
import sqlite3
import time
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional


def _resolve_default_db_path() -> Path:
    env_path = os.getenv("AD_TELEMETRY_DB_PATH")
    if env_path:
        return Path(env_path)
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return Path(tempfile.gettempdir()) / "ad_telemetry.db"
    try:
        test_file = Path("ad_telemetry_test.tmp")
        test_file.touch()
        test_file.unlink()
        return Path("ad_telemetry.db")
    except (PermissionError, OSError):
        return Path(tempfile.gettempdir()) / "ad_telemetry.db"


DEFAULT_DB_PATH = _resolve_default_db_path()


class LocalAdExchangeSandbox:
    """
    Self-contained ad telemetry tracker and second-price Vickrey auction pricing engine
    backed by local SQLite. Tracks impressions, clicks, query audits, and LLM inference cost recovery.
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

    @staticmethod
    def _calculate_llm_cost_inr(total_tokens: int) -> float:
        """Calculates attributed LLM inference cost in INR (₹0.025 per 1,000 tokens)."""
        return (float(total_tokens) / 1000.0) * 0.025

    def clear_events(self) -> None:
        """Clears all logged telemetry events and query audits for hermetic testing."""
        with self._connection() as conn:
            conn.execute("DELETE FROM ad_events")
            conn.execute("DELETE FROM query_ad_audit")
            conn.commit()
            conn.execute("VACUUM")

    def execute_realtime_auction(
        self,
        candidate_campaigns: Optional[list[dict[str, Any]]] = None,
        search_query: str = "",
        top_k: int = 3,
        category: str = "",
    ) -> list[dict[str, Any]]:
        """
        Executes a real-time Vickrey second-price auction over candidate ad campaigns.
        Sets clearing price = next competitor bid + ₹1.00 (capped at the winner's maximum bid).
        """
        candidates = candidate_campaigns or []
        if not candidates:
            return []

        query_lower = (search_query or "").lower()
        scored: list[tuple[float, dict[str, Any]]] = []

        for camp in candidates:
            keywords = camp.get("keywords", [])
            hits = sum(1 for kw in keywords if kw in query_lower)
            camp_cat = camp.get("category", "")
            cat_bonus = 50.0 if (category and camp_cat == category) else 0.0
            relevance = (hits * 10.0) + cat_bonus
            cpm = float(camp.get("cpm_inr", 300.0))
            score = (relevance * cpm) if relevance > 0 else (cpm * 0.01)
            scored.append((score, camp))

        scored.sort(key=lambda x: x[0], reverse=True)
        winners = [item[1] for item in scored[:top_k]]

        results = []
        for i, winner in enumerate(winners):
            winner_cpm = float(winner.get("cpm_inr", 300.0))
            if i + 1 < len(scored):
                clearing_price = float(scored[i + 1][1].get("cpm_inr", 250.0)) + 1.0
            else:
                clearing_price = winner_cpm * 0.85

            clearing_price = min(clearing_price, winner_cpm)
            winner_copy = dict(winner)
            winner_copy["clearing_price_inr"] = round(clearing_price, 2)
            results.append(winner_copy)

        return results

    def log_impression(
        self,
        session_id: str,
        campaign: dict[str, Any],
        total_tokens: int = 0,
    ) -> dict[str, Any]:
        """Logs a single AdBanner / SponsoredCard render impression by delegating to batch logging."""
        return self.log_batch_impressions(session_id, [campaign], total_tokens=total_tokens)

    def log_batch_impressions(
        self,
        session_id: str,
        winning_campaigns: list[dict[str, Any]],
        total_tokens: int = 0,
    ) -> dict[str, Any]:
        """
        Logs real-time sponsored card batch impressions to SQLite.
        LLM inference token cost is attributed once to the search turn.
        """
        llm_cost_inr = self._calculate_llm_cost_inr(total_tokens)
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

    def log_click(
        self,
        session_id: str,
        campaign_id: str,
        sponsor_name: str = "Sponsored Partner",
        cpc_inr: float = 42.0,
    ) -> dict[str, Any]:
        """Logs a user clicking a SponsoredCard or AdBanner CTA button."""
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
                    str(campaign_id),
                    str(sponsor_name),
                    float(cpc_inr),
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

        llm_cost_inr = self._calculate_llm_cost_inr(total_tokens)
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
