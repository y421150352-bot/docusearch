import pytest

from app.chains.rag_qa_chain import _build_llm
from app.config import LLM_API_KEY, LLM_MODEL


pytestmark = pytest.mark.integration


def test_langchain_llm_client_can_be_constructed() -> None:
    if not LLM_API_KEY:
        pytest.skip("LLM api key is not configured")

    llm = _build_llm()
    assert llm.model_name == LLM_MODEL
