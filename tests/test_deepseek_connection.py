from app.chains.rag_qa_chain import _normalize_openai_base_url
from app.config import LLM_API_KEY, LLM_BASE_URL

import pytest


pytestmark = pytest.mark.integration


def test_deepseek_configuration_is_present_for_live_checks() -> None:
    if not LLM_API_KEY:
        pytest.skip("LLM api key is not configured")

    normalized_url = _normalize_openai_base_url(LLM_BASE_URL)
    assert normalized_url.startswith("http")
    assert normalized_url.endswith("/v1")
