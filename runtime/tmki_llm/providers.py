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
        mode: str = "qa",
        history: list[dict[str, str]] | None = None,
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


def _llm_system_prompt(*, query: str, read_only_mode: bool = False, mode: str = "qa") -> str:
    from tmki_rag.retrieval import looks_like_content_summary_query

    system = (
        "Ты инженерный ассистент TMKI. Отвечай по-русски, только на основе цитат. "
        "Не выдумывай нормы и номера документов."
    )
    if mode == "analyze":
        system += (
            " Задача: структурированный разбор документа по фрагментам OCR.\n"
            "Формат ответа СТРОГО:\n"
            "СУТЬ: (1–2 предложения — о чём документ)\n"
            "ГЛАВНОЕ:\n"
            "- пункт 1\n"
            "- пункт 2\n"
            "(3–7 пунктов, только ключевое)\n"
            "ТИП: (письмо / чертёж / акт / ТТН / регламент / замечания / прочее)"
        )
    elif mode in ("summarize",) or looks_like_content_summary_query(query):
        system += (
            " Задача: кратко пересказать содержание документа по фрагментам.\n"
            "Формат:\n"
            "СУТЬ: (2–4 предложения)\n"
            "ГЛАВНОЕ:\n"
            "- 2–5 ключевых пунктов"
        )
    else:
        system += (
            " Формат: 2–4 предложения по сути, затем источники (doc_id и имя файла). "
            "Если цитат недостаточно — скажи об этом."
        )
    if read_only_mode:
        system += " Режим read-only: не предлагай действий с side-effects."
    return system


def _analysis_snippet_chars(mode: str) -> int:
    return 1200 if mode in ("analyze", "summarize") else 280


def _build_chat_messages(
    *,
    system: str,
    query: str,
    context: str,
    history: list[dict[str, str]] | None,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    if history:
        for item in history:
            role = item.get("role") or ""
            content = (item.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append(
        {
            "role": "user",
            "content": f"Вопрос: {query}\n\nЦитаты:\n{context}",
        }
    )
    return messages


class StubLlmProvider:
    """MVP заглушка (без сети)."""

    def generate(
        self,
        *,
        query: str,
        citations: list[dict[str, Any]],
        read_only_mode: bool = False,
        mode: str = "qa",
        history: list[dict[str, str]] | None = None,
    ) -> LlmGenerateResult:
        from tmki_rag.document_intel import parse_analysis_text
        from tmki_rag.retrieval import looks_like_content_summary_query

        use_analysis = mode in ("analyze", "summarize") or looks_like_content_summary_query(query)
        if citations and use_analysis:
            parts: list[str] = []
            for c in citations[:6]:
                sn = (c.get("snippet") or "").strip()
                name = c.get("file_name") or c.get("relative_path") or ""
                if sn:
                    parts.append(f"{name}: {sn[:500]}")
            body = " ".join(parts)[:1200] if parts else "фрагменты без текста"
            if mode == "analyze":
                parsed = parse_analysis_text(
                    f"СУТЬ: {body[:400]}\nГЛАВНОЕ:\n- {body[:200]}\nТИП: прочее"
                )
                answer = parsed.format_answer(file_name=citations[0].get("file_name") or "")
            else:
                answer = f"СУТЬ: {body[:600]}\n\nГЛАВНОЕ:\n- см. фрагменты выше"
            confidence = "high"
        elif citations:
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
        if history and answer:
            answer = f"{answer}\n\n(Учтено реплик в диалоге: {len(history)})"
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
        mode: str = "qa",
        history: list[dict[str, str]] | None = None,
    ) -> LlmGenerateResult:
        from tmki_rag.retrieval import looks_like_content_summary_query

        effective_mode = mode
        if effective_mode == "qa" and looks_like_content_summary_query(query):
            effective_mode = "summarize"
        context = _format_citation_context(
            citations,
            snippet_chars=_analysis_snippet_chars(effective_mode),
        )
        system = _llm_system_prompt(query=query, read_only_mode=read_only_mode, mode=effective_mode)

        payload = {
            "model": self._model,
            "messages": _build_chat_messages(
                system=system,
                query=query,
                context=context,
                history=history,
            ),
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
        mode: str = "qa",
        history: list[dict[str, str]] | None = None,
    ) -> LlmGenerateResult:
        from tmki_rag.retrieval import looks_like_content_summary_query

        effective_mode = mode
        if effective_mode == "qa" and looks_like_content_summary_query(query):
            effective_mode = "summarize"
        context = _format_citation_context(
            citations,
            snippet_chars=_analysis_snippet_chars(effective_mode),
        )
        system = _llm_system_prompt(query=query, read_only_mode=read_only_mode, mode=effective_mode)

        payload = {
            "model": self._model,
            "messages": _build_chat_messages(
                system=system,
                query=query,
                context=context,
                history=history,
            ),
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
