from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class LlmGenerateResult:
    answer: str
    confidence: str
    citations: list[dict[str, Any]]
    provider: str
    model: str | None = None
    token_usage: int | None = None


class LlmProvider(Protocol):
    def generate(
        self,
        *,
        query: str,
        citations: list[dict[str, Any]],
        read_only_mode: bool = False,
    ) -> LlmGenerateResult: ...


class StubLlmProvider:
    """MVP заглушка (без сети)."""

    def generate(
        self,
        *,
        query: str,
        citations: list[dict[str, Any]],
        read_only_mode: bool = False,
    ) -> LlmGenerateResult:
        if citations:
            snippet = citations[0].get("snippet", "")
            answer = f"По материалам проекта: {snippet[:200]}"
            confidence = "high"
        else:
            answer = f"Недостаточно источников по запросу «{query}». Уточните формулировку."
            confidence = "low"
        if read_only_mode and not citations:
            confidence = "low"
        return LlmGenerateResult(
            answer=answer,
            confidence=confidence,
            citations=citations,
            provider="stub",
        )


class OpenAiLlmProvider:
    """OpenAI Chat Completions (если задан OPENAI_API_KEY)."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str | None = None,
        base_url: str = "https://api.openai.com/v1/chat/completions",
    ) -> None:
        self._api_key = api_key
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self._base_url = base_url

    def generate(
        self,
        *,
        query: str,
        citations: list[dict[str, Any]],
        read_only_mode: bool = False,
    ) -> LlmGenerateResult:
        context = "\n".join(
            f"- {c.get('snippet', '')}" for c in citations[:6]
        ) or "Нет цитат."
        system = (
            "Ты инженерный ассистент TMKI. Отвечай по-русски, только на основе цитат. "
            "Если цитат недостаточно — скажи об этом."
        )
        if read_only_mode:
            system += " Режим read-only: не предлагай действий с side-effects."

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"Вопрос: {query}\n\nЦитаты:\n{context}",
                },
            ],
            "temperature": 0.2,
        }
        req = urllib.request.Request(
            self._base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API error {exc.code}: {body}") from exc

        answer = data["choices"][0]["message"]["content"].strip()
        usage = data.get("usage", {}).get("total_tokens")
        confidence = "high" if citations else "low"
        return LlmGenerateResult(
            answer=answer,
            confidence=confidence,
            citations=citations,
            provider="openai",
            model=self._model,
            token_usage=usage,
        )


def get_llm_provider() -> LlmProvider:
    """
    TMKI_LLM_PROVIDER=stub|openai (default stub).
    OpenAI: нужен OPENAI_API_KEY.
    """
    name = os.environ.get("TMKI_LLM_PROVIDER", "stub").lower()
    if name == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY не задан для TMKI_LLM_PROVIDER=openai")
        return OpenAiLlmProvider(key)
    return StubLlmProvider()
