from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING

from tmki_rag.folders import FolderAclContext
from tmki_rag.rls import passes_rls
from tmki_rag.scope import resolve_department_scope

if TYPE_CHECKING:
    from tmki_rag.vector import VectorChunkIndex

_TOKEN_RE = re.compile(r"[а-яёa-z0-9]{2,}", re.IGNORECASE)


def _token_in_text(word: str, text: str) -> bool:
    if len(word) < 4:
        return word in text
    for n in range(len(word), 3, -1):
        if word[:n] in text:
            return True
    return False


def _query_tokens(query: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(query.lower()) if len(t) >= 2]


def _literal_prefilter(query: str, chunk: dict[str, Any]) -> bool:
    """Дешёвый отсев: не гонять лемматизацию по всему индексу."""
    text = (chunk.get("content_preview") or "").lower()
    if not text:
        return False
    q_lower = query.lower().strip()
    if len(q_lower) >= 4 and q_lower in text:
        return True
    tokens = _query_tokens(query)
    if not tokens:
        return True
    if len(tokens) >= 2:
        return all(tok in text for tok in tokens)
    return any(tok in text for tok in tokens)


def _chunk_lemmas(chunk: dict[str, Any], text: str) -> set[str]:
    """Кеш лемм текста фрагмента прямо на chunk (считаем один раз)."""
    cached = chunk.get("_lemma_set")
    if cached is not None:
        return cached
    from tmki_rag.lemmatize import lemma_set

    lemmas = lemma_set(text)
    chunk["_lemma_set"] = lemmas
    return lemmas


def _default_score(query: str, chunk: dict[str, Any]) -> float:
    from tmki_rag.match_score import text_match_score

    text = chunk.get("content_preview") or ""
    if not text:
        return 0.0
    return text_match_score(query, text, lemma_set_fn=lambda t: _chunk_lemmas(chunk, t))


def _to_citation(chunk: dict[str, Any]) -> dict[str, Any]:
    citation: dict[str, Any] = {
        "doc_id": chunk["doc_id"],
        "page": chunk.get("page") or 1,
        "start_offset": chunk.get("start_offset"),
        "end_offset": chunk.get("end_offset"),
        "snippet": (chunk.get("content_preview") or "")[:280],
    }
    rel = chunk.get("source_relative_path")
    if rel:
        citation["relative_path"] = rel
        citation["file_name"] = chunk.get("source_file_name") or Path(str(rel)).name
    return citation


def rag_search(
    request: dict[str, Any],
    chunks: list[dict[str, Any]],
    *,
    score_fn: Callable[[str, dict[str, Any]], float] | None = None,
    folder_acl: FolderAclContext | None = None,
) -> dict[str, Any]:
    """
    RAG retrieval: RLS-фильтр до ранжирования (MUST server-side).
    Контракт: schemas/document/search-response.schema.json
    """
    from tmki_rag.match_score import significant_query_tokens

    score_fn = score_fn or _default_score
    policy_context = request["policy_context"]
    trace_id = request["trace_id"]
    query = request["query"]
    top_k = request.get("top_k", 8)
    extra_filters = request.get("filters") or {}

    department_scope = resolve_department_scope(policy_context)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    filter_applied = {
        "company_id": policy_context["company_id"],
        "project_id": policy_context["project_id"],
        "department_scope": department_scope,
        "max_clearance": policy_context.get("clearance", "internal"),
        "project_role": policy_context.get("project_role"),
    }

    if department_scope == "S_dept" and not policy_context.get("department_id"):
        return {
            "schema_version": "0.1",
            "trace_id": trace_id,
            "results": [],
            "filter_applied": filter_applied,
            "stats": {"candidates_before_rls": len(chunks), "results_after_rls": 0},
            "denied_by_policy": True,
            "occurred_at": now,
        }

    candidates_before = len(chunks)
    allowed: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        if passes_rls(
            chunk,
            policy_context,
            department_scope=department_scope,
            extra_filters=extra_filters,
            folder_acl=folder_acl,
        ):
            allowed.append((score_fn(query, chunk), chunk))

    allowed.sort(key=lambda x: x[0], reverse=True)
    pool_k = request.get("candidate_pool") or max(top_k * 4, top_k)
    from tmki_rag.match_score import (
        all_query_tokens_in_text,
        ocr_alias_tokens,
        significant_query_tokens,
        split_required_optional_tokens,
    )

    corpus_blob = "\n".join((chunk.get("content_preview") or "") for _score, chunk in allowed[:500])
    required, _optional = split_required_optional_tokens(query, corpus_blob)
    if not required:
        required = [t for t in significant_query_tokens(query) if t not in ocr_alias_tokens()]
    require_all = len(required) >= 1 and len(significant_query_tokens(query)) >= 2
    results = []
    for score, chunk in allowed[:pool_k]:
        if score <= 0:
            continue
        if require_all:
            text = chunk.get("content_preview") or ""
            must = " ".join(required)
            if not all_query_tokens_in_text(must, text):
                continue
        results.append(
            {
                "chunk_id": chunk["chunk_id"],
                "doc_id": chunk["doc_id"],
                "score": round(score, 4),
                "citation": _to_citation(chunk),
                "classification": chunk.get("classification"),
            }
        )

    results = _finalize_results(request, query, results, top_k=top_k)

    return {
        "schema_version": "0.1",
        "trace_id": trace_id,
        "results": results,
        "filter_applied": filter_applied,
        "stats": {
            "candidates_before_rls": candidates_before,
            "results_after_rls": len(results),
        },
        "occurred_at": now,
    }


def _finalize_results(
    request: dict[str, Any],
    query: str,
    results: list[dict[str, Any]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    """Cross-encoder rerank → эвристический rerank → top_k."""
    if not results:
        return []
    use_ce = request.get("cross_encoder_rerank")
    if use_ce is None:
        from tmki_rag.feature_flags import cross_encoder_rerank_enabled

        use_ce = cross_encoder_rerank_enabled()
    if use_ce:
        from tmki_rag.cross_encoder import available, rerank_results as ce_rerank

        if available():
            reranked = ce_rerank(query, results, top_k=top_k)
            if reranked:
                return reranked
    quality = request.get("quality_rerank")
    if quality is None:
        from tmki_rag.feature_flags import quality_rerank_enabled

        quality = quality_rerank_enabled()
    if quality:
        from tmki_rag.retrieval import rerank_results

        reranked = rerank_results(query, results, top_k=top_k)
        if reranked:
            return reranked
    return results[:top_k]


def _fusion_enabled(request: dict[str, Any]) -> bool:
    if request.get("rag_fusion") is False:
        return False
    if request.get("rag_fusion") is True:
        return True
    from tmki_rag.feature_flags import rag_fusion_enabled

    return rag_fusion_enabled()


def _bm25_disabled() -> bool:
    return os.environ.get("TMKI_DISABLE_BM25") == "1"


def _get_bm25_index(index: "VectorChunkIndex", allowed_chunks: list[dict[str, Any]]):
    """BM25-индекс кешируется на объекте index (строится один раз для его chunks)."""
    from tmki_rag.bm25 import Bm25Index

    cached = getattr(index, "_bm25_index", None)
    cached_n = getattr(index, "_bm25_index_n", -1)
    if cached is not None and cached_n == len(allowed_chunks):
        return cached
    bm25 = Bm25Index(allowed_chunks)
    index._bm25_index = bm25
    index._bm25_index_n = len(allowed_chunks)
    return bm25


def _full_scan_index_chunks(
    request: dict[str, Any],
    index: "VectorChunkIndex",
    *,
    score_fn: Callable[[str, dict[str, Any]], float],
    folder_acl: FolderAclContext | None,
    pool: int,
) -> list[dict[str, Any]]:
    """Полнотекстовый проход по всем chunks: keyword-скан + BM25, слитые через RRF."""
    policy_context = request["policy_context"]
    query = request["query"]
    department_scope = resolve_department_scope(policy_context)
    extra_filters = request.get("filters") or {}

    allowed: list[dict[str, Any]] = []
    scored: list[tuple[float, dict[str, Any]]] = []
    from tmki_rag.match_score import (
        all_query_tokens_in_text,
        ocr_alias_tokens,
        significant_query_tokens,
        split_required_optional_tokens,
    )

    for chunk in index.list():
        if not passes_rls(
            chunk,
            policy_context,
            department_scope=department_scope,
            extra_filters=extra_filters,
            folder_acl=folder_acl,
        ):
            continue
        allowed.append(chunk)

    corpus_blob = "\n".join((c.get("content_preview") or "") for c in allowed)
    required, _optional = split_required_optional_tokens(query, corpus_blob)
    if not required:
        required = [t for t in significant_query_tokens(query) if t not in ocr_alias_tokens()]
    require_all = len(required) >= 1 and len(significant_query_tokens(query)) >= 2
    for chunk in allowed:
        if not _literal_prefilter(query, chunk):
            continue
        if require_all:
            text = chunk.get("content_preview") or ""
            must = " ".join(required)
            if not all_query_tokens_in_text(must, text):
                continue
        score = score_fn(query, chunk)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    keyword_ranked = [chunk for _, chunk in scored[:pool]]

    if _bm25_disabled():
        return keyword_ranked

    bm25 = _get_bm25_index(index, allowed)
    if not bm25.available:
        return keyword_ranked
    bm25_ranked = [chunk for _, chunk in bm25.top(query, top_k=pool)]
    if require_all:
        must = " ".join(required)
        bm25_ranked = [
            chunk
            for chunk in bm25_ranked
            if all_query_tokens_in_text(must, chunk.get("content_preview") or "")
        ]
    if not bm25_ranked:
        return keyword_ranked

    from tmki_rag.bm25 import reciprocal_rank_fusion

    return reciprocal_rank_fusion([keyword_ranked, bm25_ranked], top_k=pool)


def _use_full_text_scan(index: "VectorChunkIndex") -> bool:
    mode = os.environ.get("TMKI_SEARCH_MODE", "auto").lower()
    if mode == "vector":
        return False
    if mode in ("keyword", "fulltext", "full"):
        return True
    try:
        from tmki_rag.pgvector import PgVectorChunkIndex
    except ImportError:
        PgVectorChunkIndex = type(None)  # type: ignore[misc, assignment]
    if isinstance(index, PgVectorChunkIndex):
        return mode == "auto" and len(index.list()) <= 5000
    return True


def rag_search_with_index(
    request: dict[str, Any],
    index: "VectorChunkIndex",
    *,
    score_fn: Callable[[str, dict[str, Any]], float] | None = None,
    folder_acl: FolderAclContext | None = None,
    candidate_pool: int | None = None,
) -> dict[str, Any]:
    """RAG через VectorChunkIndex: полный keyword/hybrid scan или vector pre-filter."""
    score_fn = score_fn or _default_score
    policy_context = request["policy_context"]
    top_k = request.get("top_k", 8)
    pool = candidate_pool or request.get("candidate_pool") or max(top_k * 8, 64)

    if _fusion_enabled(request):
        from tmki_rag.rag_fusion import expand_query_variants, fuse_chunk_rankings

        ranked_lists: list[list[dict[str, Any]]] = []
        for variant in expand_query_variants(request["query"]):
            sub = {**request, "query": variant, "rag_fusion": False}
            ranked_lists.append(
                _retrieve_chunks(sub, index, score_fn=score_fn, folder_acl=folder_acl, pool=pool)
            )
        fused = fuse_chunk_rankings([r for r in ranked_lists if r], top_k=pool)
        fusion_request = {**request, "rag_fusion": False}
        return rag_search(fusion_request, fused, score_fn=score_fn, folder_acl=folder_acl)

    chunks = _retrieve_chunks(
        request, index, score_fn=score_fn, folder_acl=folder_acl, pool=pool
    )
    return rag_search(request, chunks, score_fn=score_fn, folder_acl=folder_acl)


def _retrieve_chunks(
    request: dict[str, Any],
    index: "VectorChunkIndex",
    *,
    score_fn: Callable[[str, dict[str, Any]], float],
    folder_acl: FolderAclContext | None,
    pool: int,
) -> list[dict[str, Any]]:
    policy_context = request["policy_context"]
    if _use_full_text_scan(index):
        return _full_scan_index_chunks(
            request,
            index,
            score_fn=score_fn,
            folder_acl=folder_acl,
            pool=pool,
        )
    similar = index.search_similar(
        request["query"],
        company_id=policy_context["company_id"],
        project_id=policy_context["project_id"],
        top_k=pool,
    )
    return [chunk for _, chunk in similar]
