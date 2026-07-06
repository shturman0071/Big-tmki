"""BM25 лексический индекс + RRF-слияние с векторным поиском.

BM25 (rank_bm25) хорошо ловит точные термины, номера приказов, аббревиатуры
(ОПО, СКРУ-2), где вектор проседает. Токены лемматизируются (русские падежи).
RRF (Reciprocal Rank Fusion, k=60) честно сливает два ранкинга по рангам, а не
по несопоставимым сырым скорам. Паттерн: tim-ponomarev/hybrid-rag, acuity-rag."""

from __future__ import annotations

import os
from typing import Any

from tmki_rag.lemmatize import lemmatize_tokens

RRF_K = int(os.environ.get("TMKI_RRF_K", "60"))


class Bm25Index:
    """Ленивый BM25-индекс поверх списка chunks (строится один раз)."""

    def __init__(self, chunks: list[dict[str, Any]]) -> None:
        self._chunks = chunks
        self._bm25 = None
        self._built = False

    def _build(self) -> None:
        if self._built:
            return
        self._built = True
        if not self._chunks:
            self._bm25 = None
            return
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            self._bm25 = None
            return
        corpus = [
            lemmatize_tokens(c.get("content_preview") or "") or ["_"]
            for c in self._chunks
        ]
        self._bm25 = BM25Okapi(corpus)

    @property
    def available(self) -> bool:
        self._build()
        return self._bm25 is not None

    def top(self, query: str, *, top_k: int) -> list[tuple[float, dict[str, Any]]]:
        self._build()
        if self._bm25 is None:
            return []
        q_tokens = lemmatize_tokens(query) or [query.lower()]
        scores = self._bm25.get_scores(q_tokens)
        ranked = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:top_k]
        return [(float(scores[i]), self._chunks[i]) for i in ranked if scores[i] > 0]


def _chunk_key(chunk: dict[str, Any]) -> str:
    return str(chunk.get("chunk_id") or id(chunk))


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict[str, Any]]],
    *,
    k: int = RRF_K,
    top_k: int = 64,
) -> list[dict[str, Any]]:
    """Слить несколько ранкингов: score = sum(1/(k + rank))."""
    scores: dict[str, float] = {}
    by_key: dict[str, dict[str, Any]] = {}
    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked):
            key = _chunk_key(chunk)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            by_key.setdefault(key, chunk)
    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [by_key[key] for key, _ in ordered[:top_k]]
