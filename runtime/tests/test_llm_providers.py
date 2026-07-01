import os

import pytest

from tmki_llm import StubLlmProvider, get_llm_provider


def test_stub_provider_with_citations():
    p = StubLlmProvider()
    result = p.generate(
        query="маркшейдерская съёмка",
        citations=[{"snippet": "Маркшейдерская съёмка на участке КС"}],
    )
    assert result.provider == "stub"
    assert result.confidence == "high"
    assert "Маркшейдерская" in result.answer


def test_stub_provider_without_citations():
    p = StubLlmProvider()
    result = p.generate(query="тест", citations=[])
    assert result.confidence == "low"


def test_get_llm_provider_default_stub(monkeypatch):
    monkeypatch.delenv("TMKI_LLM_PROVIDER", raising=False)
    provider = get_llm_provider()
    assert isinstance(provider, StubLlmProvider)


def test_get_llm_provider_openai_requires_key(monkeypatch):
    monkeypatch.setenv("TMKI_LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_llm_provider()
