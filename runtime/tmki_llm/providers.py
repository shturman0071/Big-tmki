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


def _format_citation_context(
    citations: list[dict[str, Any]],
    *,
    limit: int = 6,
    snippet_chars: int = 280,
) -> str:
    lines: list[str] = []
    for i, citation in enumerate(citations[:limit], start=1):
        doc_id = citation.get("doc_id") or "?"
        file_name = citation.get("file_name") or citation.get("relative_path") or ""
        snippet = (citation.get("snippet") or "").strip()[:snippet_chars]
        header = f"[{i}] doc_id={doc_id}"
        if file_name:
            header += f" | файл: {file_name}"
        lines.append(f"{header}\n{snippet}")
    return "\n\n".join(lines) if lines else "Нет цитат."


def _llm_system_prompt(*, query: str, read_only_mode: bool = False) -> str:
    from tmki_rag.retrieval import looks_like_content_summary_query

    system = (
        "Ты инженерный ассистент TMKI. Отвечай по-русски, только на основе цитат. "
        "Не выдумывай нормы и номера документов."
    )
    if looks_like_content_summary_query(query):
        system += (
            " Задача: кратко (3–6 предложений) пересказать содержание письма или документа "
            "по приведённым фрагментам: о чём письмо, ключевые требования или замечания."
        )
    else:
        system += (
            " Формат: 2–4 предложения по сути, затем источники (doc_id и имя файла). "
            "Если цитат недостаточно — скажи об этом."
        )
    if read_only_mode:
        system += " Режим read-only: не предлагай действий с side-effects."
    return system


class StubLlmProvider:
    """MVP заглушка (без сети)."""

    def generate(
        self,
        *,
        query: str,
        citations: list[dict[str, Any]],
        read_only_mode: bool = False,
    ) -> LlmGenerateResult:
        from tmki_rag.retrieval import looks_like_content_summary_query

        if citations:
            if looks_like_content_summary_query(query):
                parts: list[str] = []
                for i, c in enumerate(citations[:4], start=1):
                    sn = (c.get("snippet") or "").strip()
                    name = c.get("file_name") or c.get("relative_path") or ""
                    if sn:
                        parts.append(f"{i}. {name}\n{sn[:700]}")
                body = "\n\n".join(parts) if parts else "фрагменты без текста"
                answer = f"Кратко по документу:\n{body}"
            else:
                first = citations[0]
                snippet = (first.get("snippet") or "").strip()
                doc_id = first.get("doc_id") or "?"
                file_name = first.get("file_name") or first.get("relative_path") or ""
                header = f"По регламентам проекта (doc_id={doc_id}"
                if file_name:
                    header += f", файл: {file_name}"
                header += "):"
                body = snippet[:420] if snippet else "фрагмент без текста"
                answer = f"{header}\n{body}"
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
        from tmki_rag.retrieval import looks_like_content_summary_query

        context = _format_citation_context(
            citations,
            snippet_chars=800 if looks_like_content_summary_query(query) else 280,
        )
        system = _llm_system_prompt(query=query, read_only_mode=read_only_mode)

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


class OllamaLlmProvider:
    """Локальный Ollama (http://127.0.0.1:11434)."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._base_url = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self._model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

    def generate(
        self,
        *,
        query: str,
        citations: list[dict[str, Any]],
        read_only_mode: bool = False,
    ) -> LlmGenerateResult:
        from tmki_rag.retrieval import looks_like_content_summary_query

        context = _format_citation_context(
            citations,
            snippet_chars=800 if looks_like_content_summary_query(query) else 280,
        )
        system = _llm_system_prompt(query=query, read_only_mode=read_only_mode)

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"Вопрос: {query}\n\nЦитаты:\n{context}"},
            ],
            "stream": False,
        }
        req = urllib.request.Request(
            f"{self._base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama API error {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama недоступен ({self._base_url}): {exc.reason}") from exc

        answer = (data.get("message") or {}).get("content", "").strip()
        confidence = "high" if citations and answer else "low"
        return LlmGenerateResult(
            answer=answer or "Пустой ответ Ollama.",
            confidence=confidence,
            citations=citations,
            provider="ollama",
            model=self._model,
        )


from tmki_runtime.secrets import is_valid_openai_api_key


def get_llm_provider() -> LlmProvider:
    """
    TMKI_LLM_PROVIDER=stub|openai|ollama (default stub).
    """
    name = os.environ.get("TMKI_LLM_PROVIDER", "stub").lower()
    if name == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        if not is_valid_openai_api_key(key):
            raise RuntimeError(
                "OPENAI_API_KEY не задан или это placeholder (sk-...) для TMKI_LLM_PROVIDER=openai"
            )
        return OpenAiLlmProvider(key or "")
    if name == "ollama":
        return OllamaLlmProvider()
    return StubLlmProvider()
