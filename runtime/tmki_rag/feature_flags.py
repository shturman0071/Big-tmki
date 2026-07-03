"""Флаги retrieval/ingest (в т.ч. отложенные интеграции)."""

from __future__ import annotations

import os


def _env_bool(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def cross_encoder_rerank_enabled() -> bool:
    """TMKI_CROSS_ENCODER_RERANK=1 — neural rerank (sentence-transformers)."""
    return _env_bool("TMKI_CROSS_ENCODER_RERANK", default=True)


def quality_rerank_enabled() -> bool:
    """Эвристический rerank (fallback без sentence-transformers)."""
    return _env_bool("TMKI_QUALITY_RERANK", default=True)


def rag_fusion_enabled() -> bool:
    """TMKI_RAG_FUSION=1 — несколько вариантов запроса + RRF."""
    return _env_bool("TMKI_RAG_FUSION", default=True)


def rag_fusion_llm_enabled() -> bool:
    """TMKI_RAG_FUSION_LLM=1 — перефразировки через Ollama (медленнее)."""
    return _env_bool("TMKI_RAG_FUSION_LLM", default=False)


def incremental_ingest_enabled() -> bool:
    """TMKI_INCREMENTAL_INGEST=1 — пропуск неизменённых файлов по mtime/size."""
    return _env_bool("TMKI_INCREMENTAL_INGEST", default=True)


def pgvector_backend_enabled() -> bool:
    """TMKI_INDEX_BACKEND=pgvector + DATABASE_URL."""
    return (
        os.environ.get("TMKI_INDEX_BACKEND", "").lower() == "pgvector"
        and bool(os.environ.get("DATABASE_URL"))
    )


def ingest_parser_backend() -> str:
    """default | docling | kreuzberg — отложенные парсеры (см. parser_backend.py)."""
    return os.environ.get("TMKI_INGEST_PARSER", "default").lower().strip() or "default"
