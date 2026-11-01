import os
from unittest.mock import patch
import pytest
from google_a2a_agent.model_router import get_adk_model, get_gemini_rate_limit_config, DEFAULT_GEMINI_MODEL


def test_google_genai_use_vertexai_is_false():
    assert os.getenv("GOOGLE_GENAI_USE_VERTEXAI") == "FALSE"


def test_gemini_is_default_sut_and_judge_model():
    # When Ollama is commented out, all roles default to Gemini
    sut_model = get_adk_model("sut")
    judge_model = get_adk_model("judge")
    assert isinstance(sut_model, str)
    assert isinstance(judge_model, str)
    assert "gemini" in sut_model.lower()
    assert "gemini" in judge_model.lower()


@patch.dict(os.environ, {"GEMINI_JUDGE_MODEL": "gemini-flash-lite-latest"})
def test_gemini_provider_returns_configured_model():
    model = get_adk_model("sut")
    assert isinstance(model, str)
    assert model == "gemini-flash-lite-latest"


def test_gemini_rate_limit_config():
    config = get_gemini_rate_limit_config()
    assert "max_rpm" in config
    assert "backoff_seconds" in config
    assert config["max_rpm"] > 0
