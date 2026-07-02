"""Вызов MVP RAG для demo UI."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import"
_INDEX_CACHE: dict[str, tuple[str, Any, list[dict[str, Any]]]] = {}
_CATALOG_CACHE: Any | None = None


def _get_catalog() -> Any:
    global _CATALOG_CACHE
    if _CATALOG_CACHE is None:
        from tmki_rag.doc_catalog import DocCatalog

        _CATALOG_CACHE = DocCatalog.load(artifacts_dir=DEFAULT_ARTIFACTS, index_paths=False)
    return _CATALOG_CACHE



def _maybe_fix_mojibake_text(value: str) -> str:
    """Repair common UTF-8-as-cp1251 mojibake in demo output."""
    markers = ("Р", "С", "Ð", "Ñ")
    if not value or sum(value.count(m) for m in markers) < 3:
        return value
    candidates: list[str] = []
    for enc in ("cp1251", "latin1"):
        try:
            candidates.append(value.encode(enc).decode("utf-8"))
        except UnicodeError:
            continue
    if not candidates:
        return value

    def score(text: str) -> int:
        cyr = sum("А" <= ch <= "я" or ch == "ё" or ch == "Ё" for ch in text)
        bad = text.count("Р") + text.count("С") + text.count("Ð") + text.count("Ñ")
        return cyr - bad * 2

    best = max(candidates, key=score)
    return best if score(best) > score(value) else value


def _clean_demo_payload(value: Any) -> Any:
    if isinstance(value, str):
        return _maybe_fix_mojibake_text(value)
    if isinstance(value, list):
        return [_clean_demo_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean_demo_payload(item) for key, item in value.items()}
    return value


def resolve_llm_provider() -> str:
    env = os.environ.get("TMKI_LLM_PROVIDER", "").lower()
    if env in ("stub", "ollama", "openai"):
        return env
    try:
        import importlib.util

        script = Path(__file__).resolve().parents[1] / "scripts" / "check_ollama.py"
        spec = importlib.util.spec_from_file_location("check_ollama", script)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.resolve_demo_llm(prefer="auto")
    except Exception:
        pass
    return "stub"


def _align_embedding_provider(llm: str) -> None:
    """Demo: всегда local embeddings (совпадает с pgvector индексом, без сети)."""
    if os.environ.get("TMKI_EMBEDDING_PROVIDER"):
        return
    os.environ["TMKI_EMBEDDING_PROVIDER"] = "local"


def _policy_context() -> dict[str, Any]:
    from tmki_policy import build_policy_context, load_org_snapshot

    snapshot = load_org_snapshot(ROOT / "schemas/org/examples/satimol-snapshot.example.json")
    return build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )


def _resolve_backend() -> tuple[str, Any | None, list[dict[str, Any]]]:
    from tmki_rag import VectorChunkIndex, get_chunk_index, load_regulations_chunks, resolve_regulations_chunks_path
    from tmki_rag.pgvector import PgVectorChunkIndex

    use_pgvector = os.environ.get("TMKI_INDEX_BACKEND", "").lower() == "pgvector" and bool(
        os.environ.get("DATABASE_URL")
    )
    if use_pgvector:
        cache_key = "pgvector"
        if cache_key in _INDEX_CACHE:
            return _INDEX_CACHE[cache_key]
        backend = get_chunk_index()
        if isinstance(backend, PgVectorChunkIndex) and backend.count() > 0:
            payload = ("pgvector", backend, [])
            _INDEX_CACHE[cache_key] = payload
            return payload
    chunks_path = resolve_regulations_chunks_path("v2")
    cache_key = f"json:{chunks_path.resolve()}"
    if cache_key in _INDEX_CACHE:
        return _INDEX_CACHE[cache_key]
    chunks = load_regulations_chunks(chunks_path)
    index = VectorChunkIndex()
    index.add(chunks)
    payload = ("json", index, [])
    _INDEX_CACHE[cache_key] = payload
    return payload


def _answer_open_intent(message: str, catalog: Any) -> dict[str, Any] | None:
    from tmki_rag.retrieval import detect_query_intent

    if detect_query_intent(message) != "open":
        return None
    matches = catalog.search_paths(message, limit=8)
    if not matches:
        return {
            "answer": (
                "Не нашёл файл по указанию в архиве. "
                "Уточните имя документа или ключевые слова из названия."
            ),
            "confidence": "low",
            "citations": [],
            "intent": "open",
            "matched_files": [],
        }
    lines = ["Нашёл файлы в архиве регламентов:"]
    citations: list[dict[str, Any]] = []
    for i, item in enumerate(matches[:6], start=1):
        lines.append(f"{i}. {item['file_name']} — {item['relative_path']}")
        citations.append(
            {
                "doc_id": item.get("doc_id") or "",
                "snippet": item["relative_path"],
                "file_name": item["file_name"],
                "relative_path": item["relative_path"],
                "absolute_path": item["absolute_path"],
            }
        )
    lines.append("\nНажмите «Открыть» у нужного источника или скопируйте путь.")
    return {
        "answer": "\n".join(lines),
        "confidence": "high" if matches else "low",
        "citations": citations,
        "intent": "open",
        "matched_files": matches,
    }


def ask_regulations(
    message: str,
    *,
    llm_provider: str | None = None,
    hybrid: bool = True,
) -> dict[str, Any]:
    from tmki_rag.doc_catalog import DocCatalog
    from tmki_rag.retrieval import detect_query_intent, normalize_query
    from tmki_runtime import run_mvp

    raw_message = message.strip()
    llm = llm_provider or resolve_llm_provider()
    _align_embedding_provider(llm)
    catalog = _get_catalog()

    open_result = _answer_open_intent(raw_message, catalog)
    if open_result is not None:
        backend_name, index, chunks = _resolve_backend()
        rows = index.count() if index is not None and hasattr(index, "count") else len(chunks)
        return {
            **_clean_demo_payload(open_result),
            "llm_provider": llm,
            "backend": backend_name,
            "index_rows": rows,
            "loop_state": "loop_complete",
            "intent": "open",
        }

    query = normalize_query(raw_message)
    backend_name, index, chunks = _resolve_backend()
    use_hybrid = hybrid and backend_name != "pgvector"
    result = run_mvp(
        message=query,
        policy_context=_policy_context(),
        chunks=chunks,
        index=index,
        use_hybrid_search=use_hybrid,
        quality_rerank=True,
        llm_provider=llm,
    )
    output = result.get("output") or {}
    if index is not None:
        if hasattr(index, "count"):
            rows = index.count()
        else:
            rows = len(index.list())
    else:
        rows = len(chunks)
    citations = catalog.enrich_citations(_clean_demo_payload(output.get("citations") or []))
    answer = _maybe_fix_mojibake_text(output.get("answer", ""))
    if llm == "stub" and citations:
        from tmki_llm.providers import StubLlmProvider

        regen = StubLlmProvider().generate(query=query, citations=citations)
        answer = _maybe_fix_mojibake_text(regen.answer)
    return {
        "answer": answer,
        "confidence": output.get("confidence", "low"),
        "citations": citations,
        "llm_provider": output.get("llm_provider") or llm,
        "backend": backend_name,
        "index_rows": rows,
        "loop_state": (result.get("loop_state") or {}).get("loop_state"),
        "intent": detect_query_intent(raw_message),
    }


def resolve_document(doc_id: str | None = None, *, query: str | None = None) -> dict[str, Any]:
    from tmki_rag.doc_catalog import DocCatalog

    catalog = _get_catalog()
    if doc_id:
        resolved = catalog.resolve_doc_id(doc_id)
        if resolved:
            return {"status": "ok", "document": resolved}
        return {"status": "not_found", "doc_id": doc_id}
    if query:
        matches = catalog.search_paths(query, limit=10)
        return {"status": "ok", "matches": matches}
    return {"status": "error", "error": "doc_id or query required"}


def pipeline_status_snapshot(*, artifacts_dir: Path | None = None) -> dict[str, Any]:
    artifacts = artifacts_dir or DEFAULT_ARTIFACTS
    state = artifacts / "reindex-state.json"
    if not state.is_file():
        return {"phase": "unknown", "detail": "reindex-state.json not found"}
    from tmki_ingest.pipeline_status import build_pipeline_status

    return build_pipeline_status(
        artifacts_dir=artifacts,
        state_path=state,
        heartbeat_path=artifacts / "reindex-heartbeat.json",
        lock_path=artifacts / "reindex.lock",
    )
