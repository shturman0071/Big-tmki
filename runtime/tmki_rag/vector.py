from __future__ import annotations

import os
from typing import Any

from tmki_rag.embeddings import cosine_similarity, text_embedding
from tmki_rag.index import ChunkIndex


class VectorChunkIndex(ChunkIndex):
    """In-memory индекс с локальными embeddings для гибридного поиска."""

    def __init__(self, chunks: list[dict[str, Any]] | None = None, *, dims: int = 64) -> None:
        super().__init__(chunks)
        self._dims = dims
        for chunk in self._chunks:
            self._ensure_embedding(chunk)

    def _ensure_embedding(self, chunk: dict[str, Any]) -> None:
        if "_embedding" not in chunk:
            chunk["_embedding"] = text_embedding(chunk.get("content_preview", ""), dims=self._dims)

    def add(self, chunks: list[dict[str, Any]]) -> int:
        prepared = []
        for chunk in chunks:
            item = dict(chunk)
            self._ensure_embedding(item)
            prepared.append(item)
        return super().add(prepared)

    def vector_score(self, query: str, chunk: dict[str, Any]) -> float:
        q_emb = text_embedding(query, dims=self._dims)
        c_emb = chunk.get("_embedding") or text_embedding(chunk.get("content_preview", ""), dims=self._dims)
        return cosine_similarity(q_emb, c_emb)


def hybrid_score_fn(index: VectorChunkIndex, keyword_score):
    def score(query: str, chunk: dict[str, Any]) -> float:
        kw = keyword_score(query, chunk)
        vec = index.vector_score(query, chunk)
        return 0.35 * kw + 0.65 * vec

    return score


def get_chunk_index() -> ChunkIndex:
    """
    TMKI_INDEX_BACKEND=memory|vector|pgvector (default memory).
    pgvector требует DATABASE_URL и optional psycopg.
    """
    backend = os.environ.get("TMKI_INDEX_BACKEND", "memory").lower()
    if backend == "pgvector":
        from tmki_rag.pgvector import PgVectorChunkIndex

        return PgVectorChunkIndex.from_env()
    if backend == "vector":
        return VectorChunkIndex()
    return ChunkIndex()
