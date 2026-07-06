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
        cache: dict[str, list[float]] = getattr(self, "_query_embed_cache", {})
        if query not in cache:
            cache[query] = self._embedding_provider.embed(query).vector
            self._query_embed_cache = cache
        return cache[query]

    def vector_score(self, query: str, chunk: dict[str, Any]) -> float:
        q_emb = self.embed_query(query)
        c_emb = chunk.get("_embedding")
        if not c_emb:
            return 0.0
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
    kw_weight = float(os.environ.get("TMKI_KEYWORD_WEIGHT", "0.5"))
    if os.environ.get("TMKI_EMBEDDING_PROVIDER", "local").lower() == "local":
        kw_weight = max(kw_weight, 0.85)

    def score(query: str, chunk: dict[str, Any]) -> float:
        kw = keyword_score(query, chunk)
        if kw >= 0.99:
            return kw
        vec = index.vector_score(query, chunk)
        return kw_weight * kw + (1.0 - kw_weight) * vec

    return score


def get_chunk_index() -> ChunkIndex:
    """
    TMKI_INDEX_BACKEND=memory|vector|pgvector (default memory).
    pgvector: TMKI_PGVECTOR_TABLE=chunks (root reindex) или tmki_chunks (runtime).
    """
    backend = os.environ.get("TMKI_INDEX_BACKEND", "memory").lower()
    if backend == "pgvector":
        table = os.environ.get("TMKI_PGVECTOR_TABLE", "chunks").lower()
        if table == "chunks":
            from tmki_rag.pgvector_simple import SimpleChunksPgIndex

            simple = SimpleChunksPgIndex.from_env()
            if simple is not None:
                return simple
        from tmki_rag.pgvector import PgVectorChunkIndex

        return PgVectorChunkIndex.from_env()
    if backend == "vector":
        dims = int(os.environ.get("TMKI_EMBEDDING_DIMS", os.environ.get("TMKI_EMBEDDING_DIM", "64")))
        return VectorChunkIndex(dims=dims)
    return ChunkIndex()
