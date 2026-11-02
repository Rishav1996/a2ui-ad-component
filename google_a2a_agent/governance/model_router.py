import os
from typing import Union, Any
from dotenv import load_dotenv

# Always load .env so GOOGLE_API_KEY, SERPAPI_API_KEY, and GEMINI_JUDGE_MODEL are present
load_dotenv()

# Ensure Google AI Studio Free Tier is targeted
if "GOOGLE_GENAI_USE_VERTEXAI" not in os.environ:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"

DEFAULT_GEMINI_MODEL = "gemini-flash-lite-latest"


def get_adk_model(role: str = "sut") -> Union[str, Any]:
    """
    Returns the configured model identifier for Google ADK LlmAgent.
    Exclusively powered by Google AI Studio Gemini.
    """
    load_dotenv()
    gemini_model = (
        os.getenv("GEMINI_JUDGE_MODEL")
        or os.getenv("GEMINI_SUT_MODEL")
        or os.getenv("GEMINI_MODEL")
        or DEFAULT_GEMINI_MODEL
    )
    return gemini_model.strip()


def get_gemini_rate_limit_config() -> dict[str, float]:
    """
    Returns rate limit configuration parameters for Google AI Studio Free Tier.
    """
    load_dotenv()
    rpm = float(os.getenv("GEMINI_FREE_TIER_RPM", "15"))
    backoff = float(os.getenv("GEMINI_RETRY_BACKOFF_SECONDS", "2.0"))
    return {
        "max_rpm": rpm,
        "backoff_seconds": backoff,
        "min_interval_seconds": 60.0 / rpm if rpm > 0 else 4.0,
    }
