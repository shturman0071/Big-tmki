from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from tmki_rag.rls import passes_rls
from tmki_rag.scope import resolve_department_scope


def _token_in_text(word: str, text: str) -> bool:
    if len(word) < 4:
        return word in text
    for n in range(len(word), 3, -1):
        if word[:n] in text:
            return True
    return False


def _default_score(query: str, chunk: dict[str, Any]) -> float:
    text = (chunk.get("content_preview") or "").lower()
    q = query.lower()
    if not text or not q:
        return 0.0
    if q in text:
        return 1.0
    words = [w for w in q.split() if w]
    if not words:
        return 0.0
    hits = sum(1 for w in words if _token_in_text(w, text))
    return float(hits) / len(words)


def _to_citation(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "doc_id": chunk["doc_id"],
        "page": chunk.get("page"),
        "start_offset": chunk.get("start_offset"),
        "end_offset": chunk.get("end_offset"),
        "snippet": (chunk.get("content_preview") or "")[:280],
    }


def rag_search(
    request: dict[str, Any],
    chunks: list[dict[str, Any]],
    *,
    score_fn: Callable[[str, dict[str, Any]], float] | None = None,
) -> dict[str, Any]:
    """
    RAG retrieval: RLS-фильтр до ранжирования (MUST server-side).
    Контракт: schemas/document/search-response.schema.json
    """
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
        if passes_rls(chunk, policy_context, department_scope=department_scope, extra_filters=extra_filters):
            allowed.append((score_fn(query, chunk), chunk))

    allowed.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, chunk in allowed[:top_k]:
        if score <= 0:
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
