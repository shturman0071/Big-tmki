"""Вызов MVP RAG для demo UI."""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import"
_INDEX_CACHE: dict[str, tuple[str, Any, list[dict[str, Any]]]] = {}
_CATALOG_CACHE: dict[str, Any] = {}
_POLICY_CACHE: dict[str, Any] | None = None
_FOLDER_ACL_CACHE: Any = None
_CHAT_STORE: Any = None


def _chat_store() -> Any:
    global _CHAT_STORE
    if _CHAT_STORE is None:
        from tmki_demo.chat_session import ChatSessionStore

        persist = Path(__file__).resolve().parents[1] / "artifacts" / "chat-sessions"
        if os.environ.get("TMKI_CHAT_PERSIST", "1").lower() not in ("0", "false", "no"):
            _CHAT_STORE = ChatSessionStore(persist_dir=persist)
        else:
            _CHAT_STORE = ChatSessionStore(persist_dir=None)
    return _CHAT_STORE


def _artifacts_dir(corpus_id: str | None = None) -> Path:
    from tmki_rag.corpus_policy import resolve_corpus_artifacts_dir

    return resolve_corpus_artifacts_dir(corpus_id)


def _get_catalog(*, corpus_id: str | None = None) -> Any:
    from tmki_rag.corpus_policy import get_corpus, resolve_corpus_archive

    cid = get_corpus(corpus_id).corpus_id
    if cid in _CATALOG_CACHE:
        return _CATALOG_CACHE[cid]
    from tmki_rag.doc_catalog import DocCatalog

    artifacts = _artifacts_dir(cid)
    catalog = DocCatalog.load(
        archive_root=resolve_corpus_archive(cid),
        artifacts_dir=artifacts,
        index_paths=False,
    )
    _CATALOG_CACHE[cid] = catalog
    return catalog



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


def resolve_llm_provider(*, corpus_id: str | None = None) -> str:
    from tmki_rag.corpus_policy import enforce_llm_for_corpus

    env = os.environ.get("TMKI_LLM_PROVIDER", "").lower()
    if env in ("stub", "ollama", "openai"):
        provider, _ = enforce_llm_for_corpus(env, corpus_id)
        return provider
    try:
        import importlib.util

        script = Path(__file__).resolve().parents[1] / "scripts" / "check_ollama.py"
        spec = importlib.util.spec_from_file_location("check_ollama", script)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            auto = mod.resolve_demo_llm(prefer="auto")
            provider, _ = enforce_llm_for_corpus(auto, corpus_id)
            return provider
    except Exception:
        pass
    provider, _ = enforce_llm_for_corpus("stub", corpus_id)
    return provider


def _apply_llm_policy(
    provider: str,
    *,
    corpus_id: str | None,
    citation_paths: list[str] | None = None,
    explicit: bool = False,
) -> tuple[str, str | None]:
    from tmki_rag.corpus_policy import enforce_llm_for_corpus, enforce_llm_for_paths

    llm, note = enforce_llm_for_corpus(provider, corpus_id, explicit=explicit)
    if citation_paths:
        llm, path_note = enforce_llm_for_paths(llm, citation_paths)
        if path_note:
            note = path_note if not note else f"{note} {path_note}"
    return llm, note


def _align_embedding_provider(llm: str) -> None:
    """Demo: embedding provider из config (ollama 768-dim или local 64-dim)."""
    if not os.environ.get("TMKI_EMBEDDING_PROVIDER"):
        os.environ["TMKI_EMBEDDING_PROVIDER"] = "ollama"
    dim = os.environ.get("TMKI_EMBEDDING_DIMS") or os.environ.get("TMKI_EMBEDDING_DIM")
    if dim and not os.environ.get("TMKI_EMBEDDING_DIMS"):
        os.environ["TMKI_EMBEDDING_DIMS"] = dim


def _policy_context() -> dict[str, Any]:
    global _POLICY_CACHE
    if _POLICY_CACHE is not None:
        return _POLICY_CACHE
    from tmki_policy import build_policy_context, load_org_snapshot

    snapshot = load_org_snapshot(ROOT / "schemas/org/examples/satimol-snapshot.example.json")
    _POLICY_CACHE = build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )
    return _POLICY_CACHE


def _folder_acl() -> Any:
    global _FOLDER_ACL_CACHE
    if _FOLDER_ACL_CACHE is None:
        from tmki_runtime.mvp import load_satimol_folder_acl

        _FOLDER_ACL_CACHE = load_satimol_folder_acl()
    return _FOLDER_ACL_CACHE


def _try_ollama_fallback(
    *,
    query: str,
    citations: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Локальный Ollama, если OpenAI недоступен (без биллинга)."""
    if os.environ.get("TMKI_DISABLE_OLLAMA_FALLBACK", "").lower() in ("1", "true", "yes"):
        return None
    try:
        os.environ["TMKI_LLM_PROVIDER"] = "ollama"
        from tmki_llm import get_llm_provider

        gen = get_llm_provider().generate(query=query, citations=citations)
        note = (
            "(Ответ через локальную Ollama — OpenAI недоступен. "
            "Для облачных ответов пополните биллинг OpenAI.)"
        )
        answer = f"{gen.answer}\n\n{note}" if gen.answer else note
        return {
            "answer": _maybe_fix_mojibake_text(answer),
            "confidence": gen.confidence or ("high" if citations else "low"),
            "citations": citations,
            "llm_provider": gen.provider or "ollama",
            "loop_state": "loop_complete",
        }
    except Exception:
        return None


def _rag_top_k() -> int:
    raw = os.environ.get("TMKI_RAG_FINAL_K") or os.environ.get("TMKI_RERANK_TOP_K") or "8"
    try:
        return max(1, int(raw))
    except ValueError:
        return 8


def _chunk_in_paths(chunk: dict[str, Any], paths: list[str]) -> bool:
    cr = (chunk.get("source_relative_path") or "").replace("\\", "/").lower()
    for p in paths:
        pl = p.replace("\\", "/").lower()
        if cr == pl or pl in cr:
            return True
    return False


def _run_content_search_in_files(
    query: str,
    *,
    index: Any,
    paths: list[str],
    llm: str,
    pool: int,
) -> dict[str, Any] | None:
    """Поиск по тексту внутри уже найденных по имени файлов (для «опиши письмо»)."""
    if index is None or not paths:
        return None
    from tmki_rag.search import rag_search

    chunks = [c for c in index.list() if _chunk_in_paths(c, paths)]
    if not chunks:
        return None
    resp = rag_search(
        {
            "policy_context": _policy_context(),
            "trace_id": "demo",
            "query": query,
            "top_k": _rag_top_k(),
            "candidate_pool": min(max(pool, 32), len(chunks)),
        },
        chunks,
        folder_acl=_folder_acl(),
    )
    citations = [r["citation"] for r in resp.get("results", [])]
    if not citations:
        return None
    os.environ["TMKI_LLM_PROVIDER"] = llm
    from tmki_llm import get_llm_provider

    try:
        gen = get_llm_provider().generate(query=query, citations=citations)
    except RuntimeError as exc:
        err = str(exc)
        if llm == "openai" and (
            "insufficient_quota" in err
            or "OpenAI API error 429" in err
            or "OpenAI API error 401" in err
        ):
            ollama_result = _try_ollama_fallback(query=query, citations=citations)
            if ollama_result is not None:
                return ollama_result
        return None
    return {
        "answer": _maybe_fix_mojibake_text(gen.answer),
        "confidence": gen.confidence or ("high" if citations else "low"),
        "citations": citations,
        "llm_provider": gen.provider or llm,
        "loop_state": "loop_complete",
    }


def _run_content_search(
    query: str,
    *,
    index: Any,
    llm: str,
    pool: int,
    corpus_id: str | None = None,
) -> dict[str, Any]:
    """Быстрый RAG для demo UI (без LoopEngine / двойного LLM)."""
    from tmki_llm import get_llm_provider
    from tmki_rag.search import rag_search_with_index

    resp = rag_search_with_index(
        {
            "policy_context": _policy_context(),
            "trace_id": "demo",
            "query": query,
            "top_k": _rag_top_k(),
            "candidate_pool": pool,
            "corpus_id": corpus_id,
        },
        index,
        folder_acl=_folder_acl(),
    )
    citations = [r["citation"] for r in resp.get("results", [])]
    os.environ["TMKI_LLM_PROVIDER"] = llm
    try:
        gen = get_llm_provider().generate(query=query, citations=citations)
    except RuntimeError as exc:
        err = str(exc)
        if llm == "openai" and (
            "insufficient_quota" in err
            or "OpenAI API error 429" in err
            or "OpenAI API error 401" in err
        ):
            ollama_result = _try_ollama_fallback(query=query, citations=citations)
            if ollama_result is not None:
                return ollama_result
            from tmki_llm.providers import StubLlmProvider

            gen = StubLlmProvider().generate(query=query, citations=citations)
            note = (
                "OpenAI недоступен (квота/ключ). Ответ по найденным фрагментам (stub). "
                "Бесплатно: установите Ollama и модель qwen2.5:7b, либо пополните "
                "https://platform.openai.com/account/billing"
            )
            answer = f"{gen.answer}\n\n{note}" if gen.answer else note
            return {
                "answer": _maybe_fix_mojibake_text(answer),
                "confidence": gen.confidence,
                "citations": citations,
                "llm_provider": "stub",
                "loop_state": "loop_complete",
            }
        raise
    confidence = gen.confidence or ("high" if citations else "low")
    return {
        "answer": _maybe_fix_mojibake_text(gen.answer),
        "confidence": confidence,
        "citations": citations,
        "llm_provider": gen.provider or llm,
        "loop_state": "loop_complete",
    }


def _ocr_alias_search(
    message: str,
    *,
    index: Any,
    llm: str,
    pool: int,
) -> dict[str, Any] | None:
    from tmki_rag.match_score import _OCR_ALIASES

    lowered = message.lower()
    for token, aliases in _OCR_ALIASES.items():
        if token not in lowered:
            continue
        for alias in aliases:
            out = _run_content_search(alias, index=index, llm=llm, pool=pool)
            if out.get("citations"):
                return out
    return None


def _missing_optional_tokens_note(message: str, index: Any) -> str | None:
    from tmki_rag.match_score import split_required_optional_tokens

    blob = "\n".join((c.get("content_preview") or "") for c in index.list())
    _required, optional = split_required_optional_tokens(message, blob)
    if optional:
        words = ", ".join(f"«{t}»" for t in optional)
        return f"В индексе не найдено: {words} (возможно, не распознано OCR или нет в документах)."
    return None


def _resolve_backend(*, corpus_id: str | None = None) -> tuple[str, Any | None, list[dict[str, Any]]]:
    from tmki_rag import get_chunk_index, load_regulations_chunks, resolve_regulations_chunks_path
    from tmki_rag.corpus_policy import get_corpus
    from tmki_rag.index import ChunkIndex
    from tmki_rag.pgvector import PgVectorChunkIndex

    cid = get_corpus(corpus_id).corpus_id
    artifacts = _artifacts_dir(cid)
    use_pgvector = (
        os.environ.get("TMKI_INDEX_BACKEND", "").lower() == "pgvector"
        and bool(os.environ.get("DATABASE_URL"))
    )
    if use_pgvector:
        cache_key = f"pgvector:{cid}:{os.environ.get('TMKI_PGVECTOR_TABLE', 'chunks')}"
        if cache_key in _INDEX_CACHE:
            return _INDEX_CACHE[cache_key]
        from tmki_rag.pgvector_simple import SimpleChunksPgIndex

        simple = SimpleChunksPgIndex.from_env()
        if simple is not None:
            rows = simple.count_for_corpus(cid)
            if rows > 0:
                payload = ("pgvector", simple, [])
                _INDEX_CACHE[cache_key] = payload
                return payload
        backend = get_chunk_index()
        if backend is not None and backend.count() > 0:
            from tmki_rag.pgvector import PgVectorChunkIndex

            if isinstance(backend, (PgVectorChunkIndex, SimpleChunksPgIndex)):
                payload = ("pgvector", backend, [])
                _INDEX_CACHE[cache_key] = payload
                return payload
    chunks_path = artifacts / "chunks-v2.json"
    if not chunks_path.is_file():
        chunks_path = resolve_regulations_chunks_path("v2")
    cache_key = f"json:{cid}:{chunks_path.resolve()}"
    if cache_key in _INDEX_CACHE:
        return _INDEX_CACHE[cache_key]
    if chunks_path.is_file():
        chunks = load_regulations_chunks(chunks_path)
    else:
        chunks = []
    index = ChunkIndex(chunks)
    payload = ("json", index, [])
    _INDEX_CACHE[cache_key] = payload
    return payload


def _regenerate_answer(
    query: str,
    citations: list[dict[str, Any]],
    llm: str,
    confidence: str,
) -> tuple[str, str, str]:
    import os

    from tmki_llm import get_llm_provider

    os.environ["TMKI_LLM_PROVIDER"] = llm
    try:
        regen = get_llm_provider().generate(query=query, citations=citations)
        return (
            _maybe_fix_mojibake_text(regen.answer),
            regen.confidence or confidence,
            regen.provider or llm,
        )
    except Exception:
        from tmki_llm.providers import StubLlmProvider

        regen = StubLlmProvider().generate(query=query, citations=citations)
        return (
            _maybe_fix_mojibake_text(regen.answer),
            regen.confidence or confidence,
            "stub",
        )


def _build_file_search_response(
    matches: list[dict[str, Any]],
    *,
    intent: str = "open",
    headline: str | None = None,
    suggested_corpus: str | None = None,
) -> dict[str, Any]:
    lines = [headline or "Нашёл файлы в архиве регламентов:"]
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
    out: dict[str, Any] = {
        "answer": "\n".join(lines),
        "confidence": "high" if matches else "low",
        "citations": citations,
        "intent": intent,
        "matched_files": matches,
    }
    if suggested_corpus:
        out["suggested_corpus"] = suggested_corpus
    return out


def _answer_open_intent(message: str, catalog: Any) -> dict[str, Any] | None:
    from tmki_rag.retrieval import detect_query_intent, looks_like_content_summary_query

    if looks_like_content_summary_query(message):
        return None
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
    return _build_file_search_response(matches, intent="open")


def _cross_corpus_file_matches(
    query: str,
    current_corpus: str,
    *,
    limit: int = 6,
) -> tuple[str, str, list[dict[str, Any]]] | None:
    from tmki_rag.corpus_policy import CORPORA, get_corpus

    best: tuple[str, str, list[dict[str, Any]], float] | None = None
    for cid in CORPORA:
        if cid == current_corpus:
            continue
        other = get_corpus(cid)
        cat = _get_catalog(corpus_id=cid)
        matches = cat.search_paths(query, limit=limit)
        if not matches:
            continue
        top_score = float(matches[0].get("score") or 0)
        if best is None or top_score > best[3]:
            best = (cid, other.label, matches, top_score)
    if best is None or best[3] < 2.0:
        return None
    return best[0], best[1], best[2]


def _fast_file_lookup(
    message: str,
    catalog: Any,
    *,
    corpus_id: str,
) -> dict[str, Any] | None:
    """Быстрый поиск по имени файла — без тяжёлого RAG (до 1–2 мин)."""
    from tmki_rag.corpus_policy import get_corpus
    from tmki_rag.retrieval import detect_query_intent, looks_like_content_summary_query, looks_like_filename_query

    if looks_like_content_summary_query(message):
        return None

    matches = catalog.search_paths(message, limit=8)
    if matches:
        top_score = float(matches[0].get("score") or 0)
        if detect_query_intent(message) == "open" and top_score >= 2.0:
            return _build_file_search_response(matches, intent="open")
        if looks_like_filename_query(message) and top_score >= 2.0:
            return _build_file_search_response(matches, intent="file")

    if not looks_like_filename_query(message):
        return None

    cross = _cross_corpus_file_matches(message, corpus_id)
    if not cross:
        return None
    other_id, other_label, other_matches = cross
    current_label = get_corpus(corpus_id).label
    headline = (
        f"В архиве «{current_label}» такого файла нет. "
        f"Найдено в «{other_label}» — переключите архив в списке выше и повторите поиск."
    )
    return _build_file_search_response(
        other_matches,
        intent="file",
        headline=headline,
        suggested_corpus=other_id,
    )


def _get_memory_store(*, corpus_id: str | None = None) -> Any:
    from tmki_rag.document_intel import DocumentMemoryStore, profiles_path

    artifacts = _artifacts_dir(corpus_id)
    return DocumentMemoryStore(profiles_path(artifacts))


def _index_chunks_list(index: Any) -> list[dict[str, Any]]:
    if index is None:
        return []
    if hasattr(index, "list"):
        return list(index.list())
    return []


def analyze_document(
    message: str,
    *,
    doc_id: str | None = None,
    relative_path: str | None = None,
    llm_provider: str | None = None,
    corpus_id: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Разбор документа: суть, главное, сохранение в локальную память."""
    from tmki_rag.corpus_policy import get_corpus
    from tmki_rag.document_intel import (
        DocumentProfile,
        chunks_to_citations,
        collect_chunks_for_doc,
        fingerprint_chunks,
        infer_doc_type_from_path,
        low_text_coverage_hint,
        parse_analysis_text,
        rank_file_matches_for_content_query,
        select_analysis_chunks,
    )
    from tmki_rag.retrieval import detect_query_intent, looks_like_content_summary_query

    raw_message = message.strip()
    corpus = get_corpus(corpus_id)
    explicit_llm = llm_provider is not None
    requested = llm_provider or resolve_llm_provider(corpus_id=corpus.corpus_id)
    llm, policy_note = _apply_llm_policy(requested, corpus_id=corpus.corpus_id, explicit=explicit_llm)
    _align_embedding_provider(llm)
    catalog = _get_catalog(corpus_id=corpus.corpus_id)
    backend_name, index, _chunks = _resolve_backend(corpus_id=corpus.corpus_id)
    all_chunks = _index_chunks_list(index)
    memory = _get_memory_store(corpus_id=corpus.corpus_id)

    target_doc_id = doc_id
    target_rel = relative_path
    file_name = ""

    if not target_rel and not target_doc_id and raw_message:
        path_matches = catalog.search_paths(raw_message, limit=8)
        ranked = rank_file_matches_for_content_query(
            raw_message,
            path_matches,
            prefer_letters=looks_like_content_summary_query(raw_message),
        )
        if ranked:
            target_rel = ranked[0].get("relative_path") or ""
            file_name = ranked[0].get("file_name") or ""

    if target_doc_id and not target_rel:
        resolved = catalog.resolve_doc_id(target_doc_id)
        if resolved:
            target_rel = resolved.get("relative_path") or ""
            file_name = resolved.get("file_name") or file_name

    if target_rel and not target_doc_id:
        full = catalog.archive_root / target_rel
        if full.is_file():
            from tmki_rag.doc_catalog import doc_id_from_path

            try:
                target_doc_id = doc_id_from_path(full)
            except OSError:
                target_doc_id = None

    doc_chunks = collect_chunks_for_doc(
        all_chunks,
        doc_id=target_doc_id,
        relative_path=target_rel,
    )
    if not doc_chunks and index is not None:
        from tmki_rag.search import rag_search

        scoped = _run_content_search_in_files(
            raw_message or target_rel or "",
            index=index,
            paths=[target_rel] if target_rel else [],
            llm=llm,
            pool=int(os.environ.get("TMKI_SEARCH_POOL", "64")),
        )
        if scoped and scoped.get("citations"):
            return {
                **scoped,
                "intent": "analyze",
                "corpus_id": corpus.corpus_id,
                "corpus_label": corpus.label,
                "llm_policy_note": policy_note,
                "backend": backend_name,
                "analysis": None,
                "from_memory": False,
            }

    fingerprint = fingerprint_chunks(doc_chunks) if doc_chunks else ""
    if target_doc_id and not force:
        cached = memory.get(target_doc_id)
        if cached and cached.content_fingerprint == fingerprint and cached.gist:
            answer = parse_analysis_text(
                f"СУТЬ: {cached.gist}\nГЛАВНОЕ:\n"
                + "\n".join(f"- {p}" for p in cached.key_points)
                + f"\nТИП: {cached.doc_type}"
            ).format_answer(file_name=file_name or Path(target_rel or "").name)
            answer = f"(Из памяти, {cached.analyzed_at[:10]})\n\n{answer}"
            return {
                "answer": answer,
                "confidence": "high",
                "citations": chunks_to_citations(select_analysis_chunks(doc_chunks)),
                "llm_provider": cached.llm_provider,
                "corpus_id": corpus.corpus_id,
                "corpus_label": corpus.label,
                "llm_policy_note": policy_note,
                "backend": backend_name,
                "intent": "analyze",
                "from_memory": True,
                "analysis": cached.to_dict(),
            }

    selected = select_analysis_chunks(doc_chunks)
    citations = chunks_to_citations(selected)
    intent = detect_query_intent(raw_message or "")
    mode = "analyze" if intent == "analyze" else "summarize"

    os.environ["TMKI_LLM_PROVIDER"] = llm
    from tmki_llm import get_llm_provider

    try:
        gen = get_llm_provider().generate(query=raw_message or "анализ документа", citations=citations, mode=mode)
    except RuntimeError as exc:
        err = str(exc)
        if llm == "openai":
            ollama_result = _try_ollama_fallback(query=raw_message, citations=citations)
            if ollama_result is not None:
                gen_answer = ollama_result.get("answer") or ""
                parsed = parse_analysis_text(gen_answer)
                ollama_result["analysis"] = {
                    "gist": parsed.gist,
                    "key_points": parsed.key_points,
                    "doc_type": parsed.doc_type,
                }
                ollama_result["intent"] = "analyze"
                ollama_result["from_memory"] = False
                return ollama_result
        raise RuntimeError(err) from exc

    parsed = parse_analysis_text(gen.answer)
    answer = parsed.format_answer(file_name=file_name or Path(target_rel or "").name)
    vision_hint = low_text_coverage_hint(doc_chunks)
    if vision_hint:
        answer = f"{answer}\n\n{vision_hint}"

    profile: DocumentProfile | None = None
    if target_doc_id and parsed.gist:
        from datetime import datetime, timezone

        profile = DocumentProfile(
            doc_id=target_doc_id,
            relative_path=target_rel or "",
            gist=parsed.gist,
            key_points=parsed.key_points,
            doc_type=parsed.doc_type or infer_doc_type_from_path(target_rel or ""),
            content_fingerprint=fingerprint,
            analyzed_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            llm_provider=gen.provider or llm,
            corpus_id=corpus.corpus_id,
        )
        memory.put(profile)

    rows = index.count() if index is not None and hasattr(index, "count") else len(all_chunks)
    return {
        "answer": answer,
        "confidence": gen.confidence,
        "citations": catalog.enrich_citations(citations),
        "llm_provider": gen.provider or llm,
        "corpus_id": corpus.corpus_id,
        "corpus_label": corpus.label,
        "llm_policy_note": policy_note,
        "backend": backend_name,
        "index_rows": rows,
        "loop_state": "loop_complete",
        "intent": mode,
        "from_memory": False,
        "analysis": profile.to_dict() if profile else {
            "gist": parsed.gist,
            "key_points": parsed.key_points,
            "doc_type": parsed.doc_type,
        },
    }


def ask_regulations(
    message: str,
    *,
    llm_provider: str | None = None,
    hybrid: bool = True,
    corpus_id: str | None = None,
) -> dict[str, Any]:
    from tmki_rag.corpus_policy import get_corpus
    from tmki_rag.retrieval import detect_query_intent, normalize_query
    from tmki_runtime import run_mvp

    raw_message = message.strip()
    corpus = get_corpus(corpus_id)
    explicit_llm = llm_provider is not None
    requested = llm_provider or resolve_llm_provider(corpus_id=corpus.corpus_id)
    llm, policy_note = _apply_llm_policy(
        requested,
        corpus_id=corpus.corpus_id,
        explicit=explicit_llm,
    )
    _align_embedding_provider(llm)
    catalog = _get_catalog(corpus_id=corpus.corpus_id)

    intent_early = detect_query_intent(raw_message)
    if intent_early in ("summarize", "analyze"):
        try:
            analyzed = analyze_document(
                raw_message,
                llm_provider=llm,
                corpus_id=corpus.corpus_id,
            )
            if analyzed.get("answer") and (analyzed.get("citations") or analyzed.get("from_memory")):
                return _clean_demo_payload(analyzed)
        except Exception:
            pass

    open_result = _answer_open_intent(raw_message, catalog)
    if open_result is not None:
        backend_name, index, chunks = _resolve_backend(corpus_id=corpus.corpus_id)
        rows = index.count() if index is not None and hasattr(index, "count") else len(chunks)
        return {
            **_clean_demo_payload(open_result),
            "llm_provider": llm,
            "corpus_id": corpus.corpus_id,
            "corpus_label": corpus.label,
            "llm_policy_note": policy_note,
            "backend": backend_name,
            "index_rows": rows,
            "loop_state": "loop_complete",
            "intent": "open",
        }

    fast_files = _fast_file_lookup(raw_message, catalog, corpus_id=corpus.corpus_id)
    if fast_files is not None:
        backend_name, index, chunks = _resolve_backend(corpus_id=corpus.corpus_id)
        rows = index.count() if index is not None and hasattr(index, "count") else len(chunks)
        payload = {
            **_clean_demo_payload(fast_files),
            "llm_provider": llm,
            "corpus_id": corpus.corpus_id,
            "corpus_label": corpus.label,
            "llm_policy_note": policy_note,
            "backend": backend_name,
            "index_rows": rows,
            "loop_state": "loop_complete",
            "intent": fast_files.get("intent", "file"),
        }
        if fast_files.get("suggested_corpus"):
            payload["suggested_corpus"] = fast_files["suggested_corpus"]
        return payload

    query = normalize_query(raw_message)
    backend_name, index, chunks = _resolve_backend(corpus_id=corpus.corpus_id)
    pool = int(os.environ.get("TMKI_SEARCH_POOL", "64"))
    from tmki_rag.retrieval import looks_like_content_summary_query
    from tmki_rag.document_intel import rank_file_matches_for_content_query

    output: dict[str, Any] | None = None
    if looks_like_content_summary_query(raw_message) and index is not None:
        path_matches = catalog.search_paths(raw_message, limit=8)
        ranked = rank_file_matches_for_content_query(
            raw_message,
            path_matches,
            prefer_letters=True,
        )
        file_paths = [m["relative_path"] for m in ranked[:3] if m.get("relative_path")]
        if file_paths:
            output = _run_content_search_in_files(
                query,
                index=index,
                paths=file_paths,
                llm=llm,
                pool=pool,
            )
    if output is None:
        output = _run_content_search(
            query, index=index, llm=llm, pool=pool, corpus_id=corpus.corpus_id
        )
    ocr_output = _ocr_alias_search(raw_message, index=index, llm=llm, pool=pool)
    if ocr_output and ocr_output.get("citations"):
        if "проминвест" in raw_message.lower():
            output = ocr_output
        else:
            main_paths = {c.get("relative_path") for c in (output.get("citations") or [])}
            if ocr_output["citations"][0].get("relative_path") not in main_paths:
                output = ocr_output
    optional_note = _missing_optional_tokens_note(raw_message, index) if index is not None else None
    if index is not None:
        if hasattr(index, "count_for_corpus"):
            rows = index.count_for_corpus(corpus.corpus_id)
        elif hasattr(index, "count"):
            rows = index.count()
        else:
            rows = len(index.list())
    else:
        rows = len(chunks)
    citations = catalog.enrich_citations(_clean_demo_payload(output.get("citations") or []))
    content_hit_count = len(citations)
    path_matches = catalog.search_paths(raw_message, limit=12)
    from tmki_rag.match_score import citation_doc_number_score, filename_contains_doc_number

    query_nums = re.findall(r"\d{2,}", raw_message)
    if query_nums:
        filtered = [
            item
            for item in path_matches
            if any(filename_contains_doc_number(item.get("file_name") or "", num) for num in query_nums)
        ]
        if filtered:
            path_matches = filtered
    seen_paths = {str(c.get("relative_path") or "") for c in citations}
    if not looks_like_content_summary_query(raw_message):
        for item in path_matches:
            rel = item.get("relative_path") or ""
            if not rel or rel in seen_paths:
                continue
            citations.append(
                {
                    "doc_id": item.get("doc_id") or "",
                    "snippet": f"Совпадение в имени файла: {item.get('file_name', '')}",
                    "file_name": item.get("file_name"),
                    "relative_path": rel,
                    "absolute_path": item.get("absolute_path"),
                }
            )
            seen_paths.add(rel)
    if query_nums:
        citations.sort(key=lambda c: citation_doc_number_score(c, query_nums), reverse=True)
    citations = citations[:8]

    # Каталог нашёл файл по имени после пустого векторного поиска — ответ иначе «нет источников».
    content_citations_before_paths = bool(_clean_demo_payload(output.get("citations") or []))
    answer_preview = output.get("answer") or ""
    if citations and not content_citations_before_paths:
        first = citations[0]
        sn = (first.get("snippet") or "").strip()
        if sn.startswith("Совпадение в имени файла") or "Недостаточно источников" in answer_preview:
            fname = first.get("file_name") or first.get("relative_path") or "документ"
            output = {
                **output,
                "answer": (
                    f"Нашёл в архиве файл «{fname}». "
                    "Текст этого файла пока не в поисковом индексе (найдено только по имени). "
                    "Откройте файл из списка источников или задайте вопрос по документу, "
                    "который уже проиндексирован."
                ),
                "confidence": "medium",
            }

    intent = detect_query_intent(raw_message)

    citation_paths = [
        str(c.get("absolute_path") or "")
        for c in citations
        if c.get("absolute_path")
    ]
    llm, path_note = _apply_llm_policy(
        llm,
        corpus_id=corpus.corpus_id,
        citation_paths=citation_paths,
        explicit=explicit_llm,
    )
    if path_note:
        policy_note = path_note if not policy_note else (
            path_note if path_note in policy_note else f"{policy_note} {path_note}"
        )

    used_llm = (output.get("llm_provider") or llm).lower()
    answer = output.get("answer", "")
    if optional_note and optional_note not in answer:
        answer = f"{answer}\n\n{optional_note}" if answer else optional_note
    confidence = output.get("confidence", "low")

    path_only = sum(
        1
        for c in citations
        if str(c.get("snippet") or "").startswith("Совпадение в имени файла")
    )
    search_debug = {
        "content_hits": content_hit_count,
        "path_only_hits": path_only,
        "path_catalog_matches": len(path_matches),
        "search_mode": (
            "file_list"
            if intent == "open"
            else ("path_only" if path_only and not content_hit_count else "content")
        ),
    }

    return {
        "answer": answer,
        "confidence": confidence,
        "citations": citations,
        "llm_provider": used_llm,
        "corpus_id": corpus.corpus_id,
        "corpus_label": corpus.label,
        "llm_policy_note": policy_note,
        "backend": backend_name,
        "index_rows": rows,
        "loop_state": output.get("loop_state"),
        "intent": intent,
        "search_debug": search_debug,
    }


def chat_message(
    message: str,
    *,
    session_id: str | None = None,
    llm_provider: str | None = None,
    corpus_id: str | None = None,
) -> dict[str, Any]:
    """Диалог с историей: follow-up в рамках сессии + RAG (Open WebUI / mem0-паттерн)."""
    from tmki_demo.chat_session import ChatTurn, augment_query_with_session, is_follow_up_query
    from tmki_rag.corpus_policy import get_corpus

    raw = message.strip()
    if not raw:
        return {"error": "message required", "session_id": session_id}

    corpus = get_corpus(corpus_id)
    store = _chat_store()
    session = store.get_or_create(session_id, corpus_id=corpus.corpus_id)

    store.append_turn(session, ChatTurn(role="user", content=raw, at=_iso_now()))

    rag_query = augment_query_with_session(raw, session)
    if is_follow_up_query(raw) and session.active_paths:
        backend_name, index, _ = _resolve_backend(corpus_id=corpus.corpus_id)
        explicit_llm = llm_provider is not None
        llm = llm_provider or resolve_llm_provider(corpus_id=corpus.corpus_id)
        llm, _ = _apply_llm_policy(llm, corpus_id=corpus.corpus_id, explicit=explicit_llm)
        pool = int(os.environ.get("TMKI_SEARCH_POOL", "64"))
        scoped = _run_content_search_in_files(
            rag_query,
            index=index,
            paths=session.active_paths,
            llm=llm,
            pool=pool,
        )
        if scoped and scoped.get("citations"):
            history = store.history_for_llm(session)
            os.environ["TMKI_LLM_PROVIDER"] = llm
            from tmki_llm import get_llm_provider

            gen = get_llm_provider().generate(
                query=raw,
                citations=scoped["citations"],
                history=history[:-1] if history else None,
            )
            answer = _maybe_fix_mojibake_text(gen.answer)
            citations = _get_catalog(corpus_id=corpus.corpus_id).enrich_citations(scoped["citations"])
            payload = {
                "answer": answer,
                "confidence": gen.confidence,
                "citations": _enrich_citation_scores(citations),
                "llm_provider": gen.provider or llm,
                "corpus_id": corpus.corpus_id,
                "corpus_label": corpus.label,
                "backend": backend_name,
                "intent": "chat_followup",
                "session_id": session.session_id,
                "follow_up": True,
                "loop_state": "loop_complete",
            }
            store.append_turn(
                session,
                ChatTurn(
                    role="assistant",
                    content=answer,
                    citations=citations,
                    doc_ids=[c.get("doc_id") or "" for c in citations if c.get("doc_id")],
                    intent="chat_followup",
                    confidence=payload["confidence"],
                    at=_iso_now(),
                ),
            )
            payload["turns"] = len(session.turns)
            return _clean_demo_payload(payload)

    result = ask_regulations(raw, llm_provider=llm_provider, corpus_id=corpus.corpus_id)
    if rag_query != raw and result.get("answer"):
        result["rag_query_expanded"] = True

    history = store.history_for_llm(session)
    citations = result.get("citations") or []
    if len(session.turns) > 1 and citations and result.get("llm_provider"):
        os.environ["TMKI_LLM_PROVIDER"] = result["llm_provider"]
        from tmki_llm import get_llm_provider

        try:
            gen = get_llm_provider().generate(
                query=raw,
                citations=citations,
                history=history[:-1] if history else None,
                mode=result.get("intent") if result.get("intent") in ("analyze", "summarize") else "qa",
            )
            if gen.answer:
                result["answer"] = _maybe_fix_mojibake_text(gen.answer)
                result["confidence"] = gen.confidence or result.get("confidence")
        except Exception:
            pass

    result["citations"] = _enrich_citation_scores(result.get("citations") or [])
    result["session_id"] = session.session_id
    result["follow_up"] = is_follow_up_query(raw)
    store.append_turn(
        session,
        ChatTurn(
            role="assistant",
            content=str(result.get("answer") or ""),
            citations=result.get("citations") or [],
            doc_ids=[c.get("doc_id") or "" for c in (result.get("citations") or []) if c.get("doc_id")],
            intent=str(result.get("intent") or "qa"),
            confidence=str(result.get("confidence") or "low"),
            at=_iso_now(),
        ),
    )
    result["turns"] = len(session.turns)
    return _clean_demo_payload(result)


def _enrich_citation_scores(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Kotaemon-style: relevance score для UI."""
    out: list[dict[str, Any]] = []
    for i, c in enumerate(citations):
        item = dict(c)
        if item.get("score") is None:
            item["score"] = round(max(0.35, 0.92 - i * 0.08), 3)
        out.append(item)
    return out


def _iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_chat_session(session_id: str) -> dict[str, Any]:
    store = _chat_store()
    session = store.get(session_id)
    if not session:
        return {"status": "not_found", "session_id": session_id}
    return {"status": "ok", "session": session.to_dict()}


def resolve_document(
    doc_id: str | None = None,
    *,
    query: str | None = None,
    corpus_id: str | None = None,
) -> dict[str, Any]:
    catalog = _get_catalog(corpus_id=corpus_id)
    if doc_id:
        resolved = catalog.resolve_doc_id(doc_id)
        if resolved:
            return {"status": "ok", "document": resolved}
        return {"status": "not_found", "doc_id": doc_id}
    if query:
        matches = catalog.search_paths(query, limit=10)
        try:
            from tmki_demo.synthetic_docs import search as synth_search

            synth = synth_search(query, limit=8)
            # Синтетика (договоры / To-do) — в начале списка для клика из UI Даши.
            seen = {str(m.get("absolute_path") or "") for m in matches}
            for hit in synth:
                key = str(hit.get("absolute_path") or "")
                if key and key not in seen:
                    matches.insert(0, hit)
                    seen.add(key)
            matches = matches[:12]
        except Exception:
            pass
        return {"status": "ok", "matches": matches}
    return {"status": "error", "error": "doc_id or query required"}


def pipeline_status_snapshot(*, artifacts_dir: Path | None = None, corpus_id: str | None = None) -> dict[str, Any]:
    artifacts = artifacts_dir or _artifacts_dir(corpus_id)
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
