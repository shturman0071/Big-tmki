"""Улучшения retrieval для регламентов: качество фрагментов, rerank, intent."""

from __future__ import annotations

import re
from typing import Any, Callable

_OPEN_INTENT = re.compile(
    r"(?:^|\b)(?:открой|открыть|найди\s+файл|найти\s+файл|покажи\s+документ|"
    r"где\s+(?:лежит|находится)|путь\s+к\s+файлу|путь\s+к\s+документу|"
    r"open|find\s+file|show\s+document)(?:\b|$)",
    re.IGNORECASE,
)

_COORD_NOISE = re.compile(r"^\s*[\d\s.,\-+]+(?:\s*[\d\s.,\-+]+)*\s*$")
_TOKEN_RE = re.compile(r"[а-яёa-z0-9]{3,}", re.IGNORECASE)


def detect_query_intent(query: str) -> str:
    """qa — ответ по содержанию; open — найти/открыть файл по указанию."""
    if _OPEN_INTENT.search(query.strip()):
        return "open"
    return "qa"


def normalize_query(query: str) -> str:
    """Лёгкая нормализация инженерных запросов (без LLM)."""
    q = " ".join(query.split())
    replacements = {
        "ростех надзор": "ростехнадзор",
        "ро технадзор": "ростехнадзор",
        "опо ": "опасный производственный объект ",
        "пром безопасность": "промбезопасность",
        "маркшейдерскую": "маркшейдерская",
        "маркшейдерской": "маркшейдерская",
    }
    lowered = q.lower()
    for src, dst in replacements.items():
        if src in lowered:
            q = re.sub(re.escape(src), dst, q, flags=re.IGNORECASE)
    return q.strip()


def _cyrillic_ratio(text: str) -> float:
    if not text:
        return 0.0
    cyr = sum("а" <= ch.lower() <= "я" or ch.lower() == "ё" for ch in text)
    return cyr / len(text)


def _digit_ratio(text: str) -> float:
    if not text:
        return 0.0
    return sum(ch.isdigit() for ch in text) / len(text)


def chunk_text_quality(text: str) -> float:
    """
    0..1: насколько фрагмент похож на осмысленный текст регламента.
    Отсекает координаты, таблицы чисел, пустые OCR-заглушки.
    """
    preview = (text or "").strip()
    if not preview or preview == "Документ TMKI: stub OCR content.":
        return 0.0
    if len(preview) < 24:
        return 0.15
    if _COORD_NOISE.match(preview[:120]):
        return 0.05
    cyr = _cyrillic_ratio(preview)
    digits = _digit_ratio(preview)
    if digits > 0.55 and cyr < 0.08:
        return 0.1
    if cyr < 0.12 and digits > 0.25:
        return 0.2
    score = 0.35 + min(cyr, 0.55) + min(len(preview) / 400.0, 0.25)
    if digits > 0.4:
        score -= 0.15
    return max(0.0, min(1.0, score))


def keyword_overlap(query: str, text: str) -> float:
    q_tokens = set(_TOKEN_RE.findall(query.lower()))
    if not q_tokens:
        return 0.0
    t_lower = text.lower()
    hits = sum(1 for tok in q_tokens if tok in t_lower)
    return hits / len(q_tokens)


def rerank_results(query: str, results: list[dict[str, Any]], *, top_k: int = 8) -> list[dict[str, Any]]:
    """Переранжировать RAG-результаты: качество текста + пересечение с запросом."""
    if not results:
        return []
    scored: list[tuple[float, dict[str, Any]]] = []
    seen_docs: set[str] = set()
    for item in results:
        citation = item.get("citation") or {}
        snippet = citation.get("snippet") or item.get("content_preview") or ""
        base = float(item.get("score") or 0.0)
        quality = chunk_text_quality(snippet)
        if quality < 0.12:
            continue
        overlap = keyword_overlap(query, snippet)
        doc_id = item.get("doc_id") or citation.get("doc_id") or ""
        diversity_penalty = 0.08 if doc_id and doc_id in seen_docs else 0.0
        if doc_id:
            seen_docs.add(doc_id)
        final = base * (0.45 + 0.55 * quality) + 0.35 * overlap - diversity_penalty
        scored.append((final, {**item, "score": round(final, 4)}))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_k]]


def quality_aware_score_fn(
    base_score_fn: Callable[[str, dict[str, Any]], float],
) -> Callable[[str, dict[str, Any]], float]:
    """Обёртка над score_fn: шумные фрагменты получают низкий вес."""

    def score(query: str, chunk: dict[str, Any]) -> float:
        base = base_score_fn(query, chunk)
        if base <= 0:
            return 0.0
        quality = chunk_text_quality(chunk.get("content_preview") or "")
        if quality < 0.12:
            return 0.0
        overlap = keyword_overlap(query, chunk.get("content_preview") or "")
        return base * (0.5 + 0.5 * quality) + 0.2 * overlap

    return score
