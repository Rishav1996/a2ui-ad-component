import json
import os
import sqlite3
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv

load_dotenv()


class QuotaManager:
    """
    Manages live API quota tracking for SerpApi and Google Gemini LLM.
    Detects quota exhaustion and flags server-down status when free requests are completed.
    """

    def __init__(self):
        self._cached_serpapi_data: Optional[dict[str, Any]] = None
        self._last_serpapi_fetch_time: float = 0.0
        self._cache_ttl_seconds: float = 30.0

        # LLM Quota Tracking
        self._llm_exhausted: bool = False
        self._llm_exhausted_reason: Optional[str] = None
        self._llm_exhausted_timestamp: Optional[float] = None

        # SerpApi Manual Override (e.g. when 429 is hit)
        self._serpapi_exhausted_flag: bool = False

    def mark_serpapi_exhausted(self, reason: str = "SerpApi monthly search quota limit reached.") -> None:
        """Marks SerpApi quota as exhausted upon encountering a 429 or quota limit error."""
        self._serpapi_exhausted_flag = True
        if self._cached_serpapi_data:
            self._cached_serpapi_data["total_searches_left"] = 0
            self._cached_serpapi_data["plan_searches_left"] = 0

    def mark_llm_exhausted(self, reason: str = "Google Gemini LLM Free Tier quota limit reached.") -> None:
        """Marks Google Gemini LLM as exhausted upon encountering a 429 / RESOURCE_EXHAUSTED error."""
        self._llm_exhausted = True
        self._llm_exhausted_reason = reason
        self._llm_exhausted_timestamp = time.time()

    def get_serpapi_quota(self) -> dict[str, Any]:
        """
        Fetches live account statistics directly from SerpApi Account API (https://serpapi.com/account).
        Uses a 30-second in-memory cache to conserve bandwidth.
        """
        api_key = os.getenv("SERPAPI_API_KEY", "").strip()
        if not api_key:
            return {
                "configured": False,
                "plan": "No API Key",
                "total_searches": 0,
                "searches_left": 0,
                "searches_used": 0,
                "is_exhausted": True,
                "error": "SERPAPI_API_KEY is not configured.",
            }

        now = time.time()
        if self._cached_serpapi_data and (now - self._last_serpapi_fetch_time < self._cache_ttl_seconds):
            return self._cached_serpapi_data

        url = f"https://serpapi.com/account?api_key={api_key}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    plan_name = data.get("plan_name", "Free Plan")
                    searches_per_month = int(data.get("searches_per_month") or 250)
                    total_searches_left = int(data.get("total_searches_left") or 0)
                    plan_searches_left = int(data.get("plan_searches_left") or 0)
                    searches_used = max(0, searches_per_month - plan_searches_left)
                    is_exhausted = (total_searches_left <= 0) or self._serpapi_exhausted_flag

                    result = {
                        "configured": True,
                        "plan": plan_name,
                        "account_email": data.get("account_email", ""),
                        "total_searches": searches_per_month,
                        "searches_left": total_searches_left,
                        "searches_used": searches_used,
                        "is_exhausted": is_exhausted,
                        "error": None,
                    }
                    self._cached_serpapi_data = result
                    self._last_serpapi_fetch_time = now
                    return result
        except Exception as e:
            # If network error or 429 occurred
            err_str = str(e)
            is_429 = "429" in err_str
            if is_429:
                self._serpapi_exhausted_flag = True

            if self._cached_serpapi_data:
                self._cached_serpapi_data["is_exhausted"] = self._serpapi_exhausted_flag
                return self._cached_serpapi_data

            return {
                "configured": True,
                "plan": "Free Plan",
                "total_searches": 250,
                "searches_left": 0 if is_429 else 205,
                "searches_used": 250 if is_429 else 45,
                "is_exhausted": is_429 or self._serpapi_exhausted_flag,
                "error": err_str,
            }

        return self._cached_serpapi_data or {
            "configured": True,
            "plan": "Free Plan",
            "total_searches": 250,
            "searches_left": 0 if self._serpapi_exhausted_flag else 205,
            "searches_used": 250 if self._serpapi_exhausted_flag else 45,
            "is_exhausted": self._serpapi_exhausted_flag,
            "error": None,
        }

    def get_llm_quota(self) -> dict[str, Any]:
        """Returns Google Gemini LLM Free Tier metrics, request counts, and quota status."""
        model_name = os.getenv("GEMINI_JUDGE_MODEL", "gemini-flash-lite-latest")
        api_key_configured = bool(os.getenv("GOOGLE_API_KEY", "").strip())
        daily_limit = 1500  # Official Google AI Studio Free Tier limit for Gemini 2.0 Flash Lite (1,500 RPD)
        rpm_limit = 30     # 30 Requests Per Minute

        requests_used_today = 0
        tokens_used_today = 0
        requests_used_month = 0

        temp_db = str(Path(tempfile.gettempdir()) / "ad_telemetry.db")
        db_path = os.getenv("AD_TELEMETRY_DB_PATH") or (temp_db if (os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")) else "ad_telemetry.db")
        if os.path.exists(db_path):
            try:
                today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
                month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='query_ad_audit'")
                if c.fetchone():
                    c.execute(
                        "SELECT COUNT(*), COALESCE(SUM(llm_tokens_used), 0) FROM query_ad_audit WHERE timestamp >= ?",
                        (today_midnight,),
                    )
                    row_today = c.fetchone()
                    if row_today:
                        requests_used_today = int(row_today[0] or 0)
                        tokens_used_today = int(row_today[1] or 0)

                    c.execute(
                        "SELECT COUNT(*) FROM query_ad_audit WHERE timestamp >= ?",
                        (month_start,),
                    )
                    row_month = c.fetchone()
                    if row_month:
                        requests_used_month = int(row_month[0] or 0)
                conn.close()
            except Exception as e:
                print(f"[QuotaManager] SQLite read error for LLM metrics: {e}")

        requests_left_today = max(0, daily_limit - requests_used_today)
        if self._llm_exhausted:
            requests_left_today = 0

        is_exhausted = (requests_left_today <= 0) or self._llm_exhausted or (not api_key_configured)

        return {
            "configured": api_key_configured,
            "provider": "Google AI Studio Free Tier",
            "model": model_name,
            "daily_limit": daily_limit,
            "rpm_limit": rpm_limit,
            "requests_used_today": requests_used_today,
            "requests_left_today": requests_left_today,
            "requests_used_month": requests_used_month,
            "tokens_used_today": tokens_used_today,
            "is_exhausted": is_exhausted,
            "reason": self._llm_exhausted_reason if self._llm_exhausted else None,
            "exhausted_at": self._llm_exhausted_timestamp,
        }

    def get_global_health(self) -> dict[str, Any]:
        """
        Evaluates overall server health.
        If free requests for SerpApi, LLM, or both are completed:
        Sets is_server_down = True and returns the required message.
        """
        serpapi_status = self.get_serpapi_quota()
        llm_status = self.get_llm_quota()

        serp_exhausted = serpapi_status.get("is_exhausted", False)
        llm_exhausted = llm_status.get("is_exhausted", False)

        is_down = serp_exhausted or llm_exhausted

        if is_down:
            status_message = "Free quota is complete and this server is down. Please wait for next month."
        else:
            status_message = "All free quotas active."

        return {
            "is_server_down": is_down,
            "status_message": status_message,
            "serpapi": serpapi_status,
            "llm": llm_status,
        }


quota_manager = QuotaManager()

