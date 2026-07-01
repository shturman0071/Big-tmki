from __future__ import annotations

import os
from typing import Any

from tmki_rag.embedding_providers import EmbeddingProvider, get_embedding_provider
from tmki_rag.embeddings import cosine_similarity
from tmki_rag.index import ChunkIndex


class VectorChunkIndex(ChunkIndex):
    """In-memory индекс с embeddings для гибридного поиска."""

    def __init__(
        self,
        chunks: list[dict[str, Any]] | None = None,
        *,
        dims: int = 64,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        super().__init__(chunks)
        self._embedding_provider = embedding_provider or get_embedding_provider()
        self._dims = dims
        for chunk in self._chunks:
            self._ensure_embedding(chunk)

    def _ensure_embedding(self, chunk: dict[str, Any]) -> None:
        if "_embedding" not in chunk:
            result = self._embedding_provider.embed(chunk.get("content_preview", ""))
            chunk["_embedding"] = result.vector
            chunk["embedding_model"] = result.model
            chunk["embedding_dimensions"] = result.dimensions

    def add(self, chunks: list[dict[str, Any]]) -> int:
        prepared = []
        for chunk in chunks:
            item = dict(chunk)
            self._ensure_embedding(item)
            prepared.append(item)
        return super().add(prepared)

    def embed_query(self, query: str) -> list[float]:
        return self._embedding_provider.embed(query).vector

    def vector_score(self, query: str, chunk: dict[str, Any]) -> float:
        q_emb = self.embed_query(query)
        c_emb = chunk.get("_embedding")
        if not c_emb:
            self._ensure_embedding(chunk)
            c_emb = chunk["_embedding"]
        return cosine_similarity(q_emb, c_emb)

    def search_similar(
        self,
        query: str,
        *,
        company_id: str,
        project_id: str,
        top_k: int = 20,
    ) -> list[tuple[float, dict[str, Any]]]:
        q_emb = self.embed_query(query)
        scored: list[tuple[float, dict[str, Any]]] = []
        for chunk in self._chunks:
            if chunk.get("company_id") != company_id or chunk.get("project_id") != project_id:
                continue
            sim = cosine_similarity(q_emb, chunk.get("_embedding", []))
            scored.append((sim, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]


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
