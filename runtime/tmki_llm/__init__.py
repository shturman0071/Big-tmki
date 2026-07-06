"""LLM providers (stub + optional OpenAI)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tmki_llm.providers import LlmGenerateResult, OllamaLlmProvider, StubLlmProvider


def get_llm_provider():
    from tmki_llm.providers import get_llm_provider as _get

    return _get()


def __getattr__(name: str):
    if name in ("LlmGenerateResult", "OllamaLlmProvider", "StubLlmProvider"):
        from tmki_llm import providers

        return getattr(providers, name)
    raise AttributeError(name)


__all__ = ["LlmGenerateResult", "OllamaLlmProvider", "StubLlmProvider", "get_llm_provider"]
