"""Cross-encoder rerank поверх hybrid retrieval (паттерн sec-rag / knowledge-rag)."""

from __future__ import annotations

import os
from typing import Any

_MODEL: Any = None
_MODEL_NAME: str | None = None
_MODEL_FAILED = False

DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _model_name() -> str:
    return os.environ.get("TMKI_CROSS_ENCODER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _load_model():
    global _MODEL, _MODEL_NAME, _MODEL_FAILED
    if _MODEL_FAILED:
        return None
    name = _model_name()
    if _MODEL is not None and _MODEL_NAME == name:
        return _MODEL
    try:
        from sentence_transformers import CrossEncoder

        _MODEL = CrossEncoder(name)
        _MODEL_NAME = name
        return _MODEL
    except Exception:
        _MODEL_FAILED = True
        return None


def available() -> bool:
    return _load_model() is not None


def rerank_results(
    query: str,
    results: list[dict[str, Any]],
    *,
    top_k: int = 8,
    min_score: float | None = None,
) -> list[dict[str, Any]]:
    """Переранжировать RAG-результаты cross-encoder'ом; при недоступности — без изменений."""
    if not results:
        return []
    model = _load_model()
    if model is None:
        return results[:top_k]

    cutoff = min_score
    if cutoff is None:
        try:
            cutoff = float(os.environ.get("TMKI_CROSS_ENCODER_MIN_SCORE", "0.0"))
        except ValueError:
            cutoff = 0.0

    pairs: list[tuple[str, str]] = []
    for item in results:
        citation = item.get("citation") or {}
        snippet = citation.get("snippet") or item.get("content_preview") or ""
        pairs.append((query, snippet[:2000]))

    try:
        scores = model.predict(pairs)
    except Exception:
        return results[:top_k]

    scored: list[tuple[float, dict[str, Any]]] = []
    for item, raw_score in zip(results, scores):
        score = float(raw_score)
        if score < cutoff:
            continue
        scored.append((score, {**item, "score": round(score, 4), "rerank": "cross_encoder"}))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_k]]
