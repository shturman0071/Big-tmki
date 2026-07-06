"""Голосовой диалог по открытому проиндексированному документу."""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from tmki_rag.corpus_policy import get_corpus, resolve_corpus_archive, resolve_corpus_artifacts_dir
from tmki_rag.doc_catalog import DocCatalog

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = Path(__file__).resolve().parents[1]
SESSIONS_DIR = RUNTIME / "artifacts" / "demo" / "voice-doc-sessions"

_VIEWABLE = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff"})
_TEXT_PREVIEW = frozenset({".doc", ".docx", ".txt", ".rtf", ".xlsx", ".xls", ".csv", ".ppt", ".pptx"})
_NO_ANSWER = "Нет ответа в документе."
TurnKind = Literal["user_question", "user_answer", "ai_quiz", "user_feedback"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def _load_session(session_id: str) -> dict[str, Any] | None:
    path = _session_path(session_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _save_session(state: dict[str, Any]) -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    _session_path(state["session_id"]).write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _catalog(corpus_id: str) -> DocCatalog:
    corpus = get_corpus(corpus_id)
    artifacts = resolve_corpus_artifacts_dir(corpus.corpus_id)
    return DocCatalog.load(
        archive_root=resolve_corpus_archive(corpus.corpus_id),
        artifacts_dir=artifacts,
    )


def _enrich_doc(corpus_id: str, relative_path: str) -> dict[str, Any]:
    catalog = _catalog(corpus_id)
    rel = relative_path.replace("\\", "/").lstrip("/")
    full = catalog.archive_root / rel
    fmt = full.suffix.lstrip(".").lower() if full.suffix else ""
    ext = f".{fmt}" if fmt else ""
    return {
        "corpus_id": corpus_id,
        "relative_path": rel,
        "file_name": full.name if full.name else Path(rel).name,
        "absolute_path": str(full) if full.is_file() else None,
        "format": fmt,
        "exists": full.is_file(),
        "view_mode": (
            "embed"
            if ext in _VIEWABLE
            else "preview"
            if ext in _TEXT_PREVIEW
            else "external"
        ),
    }


def preview_document_text(*, corpus_id: str, relative_path: str, max_chars: int = 50000) -> dict[str, Any]:
    from tmki_demo.qa_lab import resolve_archive_file
    from tmki_ocr.extractors import extract_local_text, guess_suffix

    target = resolve_archive_file(corpus_id=corpus_id, relative_path=relative_path)
    if not target:
        raise FileNotFoundError("file not found")
    raw = target.read_bytes()
    suffix = target.suffix.lower() or guess_suffix(raw, target.name)
    extracted = extract_local_text(
        raw,
        suffix=suffix,
        source_name=target.name,
    )
    text = (extracted.get("text") or "").strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n…"
    return {
        "corpus_id": corpus_id,
        "relative_path": relative_path.replace("\\", "/").lstrip("/"),
        "format": suffix.lstrip("."),
        "text": text,
        "readable": bool(text),
        "method": extracted.get("method"),
        "chars": len(text),
    }


def list_documents(*, corpus_id: str = "skru-2", query: str = "", limit: int = 40) -> dict[str, Any]:
    catalog = _catalog(corpus_id)
    q = query.strip()
    if q:
        items = catalog.search_paths(q, limit=limit)
    else:
        catalog._ensure_path_index()
        items = [
            {
                "relative_path": rel,
                "file_name": Path(rel).name,
                "absolute_path": str(catalog.archive_root / rel),
                "score": 0.0,
            }
            for rel in catalog.paths[:limit]
        ]
    return {"corpus_id": corpus_id, "query": q, "total": len(items), "items": items}


def open_document(
    *,
    corpus_id: str = "skru-2",
    relative_path: str,
    session_id: str | None = None,
    llm: str = "ollama",
) -> dict[str, Any]:
    doc = _enrich_doc(corpus_id, relative_path)
    if not doc.get("exists"):
        raise FileNotFoundError(f"файл не найден: {relative_path}")
    sid = session_id or f"vd_{uuid.uuid4().hex[:12]}"
    state: dict[str, Any] = {
        "session_id": sid,
        "corpus_id": corpus_id,
        "document": doc,
        "llm": llm,
        "turns": [],
        "pending_ai_question": None,
        "corrections": [],
        "created_at": _now(),
    }
    greeting = "Задайте вопрос голосом или нажмите «Спроси меня»."
    state["turns"].append({"role": "assistant", "kind": "system", "text": greeting, "at": _now()})
    _save_session(state)
    out = get_session_snapshot(sid)
    out["greeting"] = greeting
    out["tts"] = synthesize_tts_payload(greeting)
    return out


def get_session_snapshot(session_id: str) -> dict[str, Any]:
    state = _load_session(session_id)
    if not state:
        return {"session_id": session_id, "error": "session not found"}
    return {
        "session_id": state["session_id"],
        "corpus_id": state.get("corpus_id"),
        "document": state.get("document"),
        "turns": state.get("turns") or [],
        "pending_ai_question": state.get("pending_ai_question"),
        "llm": state.get("llm"),
        "updated_at": state.get("updated_at"),
    }


def _doc_citations(corpus_id: str, relative_path: str) -> list[dict[str, Any]]:
    from tmki_demo.qa import _index_chunks_list, _resolve_backend
    from tmki_rag.document_intel import chunks_to_citations, collect_chunks_for_doc, select_analysis_chunks

    _, index, _ = _resolve_backend(corpus_id=corpus_id)
    chunks = collect_chunks_for_doc(_index_chunks_list(index), relative_path=relative_path)
    return chunks_to_citations(select_analysis_chunks(chunks))


def _preview_citation(*, corpus_id: str, relative_path: str, max_chars: int = 6000) -> dict[str, Any] | None:
    try:
        preview = preview_document_text(corpus_id=corpus_id, relative_path=relative_path, max_chars=max_chars)
    except (OSError, FileNotFoundError):
        return None
    text = (preview.get("text") or "").strip()
    if not text:
        return None
    return {
        "doc_id": "preview",
        "snippet": text,
        "file_name": Path(relative_path).name,
        "relative_path": relative_path.replace("\\", "/").lstrip("/"),
        "source": "file_preview",
    }


def _merge_citations(*parts: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in parts:
        for citation in group or []:
            snippet = (citation.get("snippet") or "").strip()
            if not snippet:
                continue
            source = citation.get("source") or "index"
            key = f"{source}:{len(snippet)}:{snippet[:120]}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(citation)
    preview = next((c for c in merged if c.get("source") == "file_preview"), None)
    if preview:
        merged = [preview] + [c for c in merged if c is not preview]
    return merged


def _voice_citations_for_question(
    corpus_id: str,
    relative_path: str,
    question: str,
) -> list[dict[str, Any]]:
    import os

    from tmki_demo.qa import (
        _folder_acl,
        _index_chunks_list,
        _policy_context,
        _rag_top_k,
        _resolve_backend,
    )
    from tmki_rag.document_intel import chunks_to_citations
    from tmki_rag.document_intel import collect_chunks_for_doc
    from tmki_rag.search import rag_search

    preview = _preview_citation(corpus_id=corpus_id, relative_path=relative_path)
    _, index, _ = _resolve_backend(corpus_id=corpus_id)
    if index is None or not relative_path:
        return [preview] if preview else []

    chunks = collect_chunks_for_doc(_index_chunks_list(index), relative_path=relative_path)
    if not chunks:
        return [preview] if preview else []

    pool = int(os.environ.get("TMKI_SEARCH_POOL", "64"))
    resp = rag_search(
        {
            "policy_context": _policy_context(),
            "trace_id": "voice-doc",
            "query": question,
            "top_k": _rag_top_k(),
            "candidate_pool": min(max(pool, 32), len(chunks)),
        },
        chunks,
        folder_acl=_folder_acl(),
    )
    ranked = [r["citation"] for r in resp.get("results", []) if r.get("citation")]
    if not ranked:
        ranked = chunks_to_citations(chunks[:4])
    return _merge_citations([preview] if preview else None, ranked)


def _strip_voice_boilerplate(text: str) -> str:
    import re

    cleaned: list[str] = []
    for line in (text or "").splitlines():
        item = line.strip()
        if not item:
            continue
        if re.match(r"^(суть|главное|тип)\s*:", item, re.I):
            continue
        if item.startswith("(Из памяти"):
            continue
        if re.match(r"^документ\s*[«\"]", item, re.I):
            continue
        if re.match(r"^файл\s*[«\"]", item, re.I):
            continue
        if re.match(r"^источник\s*:", item, re.I):
            continue
        if re.search(r"doc_id\s*=", item, re.I):
            continue
        cleaned.append(line)
    out = "\n".join(cleaned).strip()
    return out or (text or "").strip()


def _is_no_answer(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return True
    markers = (
        "нет ответа",
        "недостаточно источник",
        "не удалось найти",
        "не найден",
        "не знаю",
        "нет данных",
        "информации нет",
    )
    return any(m in t for m in markers)


def _parse_user_correction(text: str) -> str | None:
    import re

    raw = (text or "").strip()
    if not raw:
        return None
    patterns = (
        r"(?:не\s*правильно|неправильно|неверно|ошибка)\s*[.:,—-]?\s*(.+)$",
        r"(?:правильно|верно|должно\s+быть)\s*[.:,—-]?\s*(.+)$",
        r"^нет\s*[,:—-]\s*(.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, re.I | re.S)
        if match:
            correction = match.group(1).strip(" .\"'").rstrip(".")
            if correction and correction.lower() not in raw.lower()[:20]:
                return correction
            if correction:
                return correction
    if len(raw) > 12 and not raw.endswith("?"):
        return raw
    return None


def _answer_voice_question(
    *,
    question: str,
    corpus_id: str,
    relative_path: str,
    llm: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    citations = _voice_citations_for_question(corpus_id, relative_path, question)
    if not citations:
        return _NO_ANSWER

    import os

    if os.environ.get("TMKI_RLM_ENABLED", "").strip() in ("1", "true", "yes"):
        from tmki_llm.rlm import rlm_answer

        preview = _preview_citation(corpus_id=corpus_id, relative_path=relative_path)
        ctx = (preview or {}).get("snippet") or ""
        if ctx:
            try:
                rlm = rlm_answer(ctx=ctx, question=question, model=llm)
                answer = _strip_voice_boilerplate((rlm.get("answer") or "").strip())
                if answer and not _is_no_answer(answer):
                    return answer
            except Exception:
                pass

    answer = _llm_text(prompt=question, citations=citations, llm=llm, history=history, mode="voice")
    answer = _strip_voice_boilerplate(answer)
    if _is_no_answer(answer):
        preview_only = _preview_citation(corpus_id=corpus_id, relative_path=relative_path)
        if preview_only:
            answer = _llm_text(
                prompt=question,
                citations=[preview_only],
                llm=llm,
                history=history,
                mode="voice",
            )
            answer = _strip_voice_boilerplate(answer)
    if _is_no_answer(answer):
        return _NO_ANSWER
    return answer


def _answer_from_document(
    *,
    question: str,
    corpus_id: str,
    relative_path: str,
    llm: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    from tmki_demo.qa import analyze_document

    try:
        return analyze_document(
            question,
            relative_path=relative_path,
            llm_provider=llm,
            corpus_id=corpus_id,
        )
    except Exception:
        from tmki_demo.qa import ask_regulations

        return ask_regulations(
            f"{question} {Path(relative_path).name}",
            llm_provider=llm,
            corpus_id=corpus_id,
        )


def _llm_text(
    *,
    prompt: str,
    citations: list[dict[str, Any]],
    llm: str,
    history: list[dict[str, str]] | None = None,
    mode: str = "qa",
) -> str:
    import os

    os.environ["TMKI_LLM_PROVIDER"] = llm
    from tmki_llm import get_llm_provider

    gen = get_llm_provider().generate(
        query=prompt,
        citations=citations,
        history=history,
        mode=mode,
    )
    return (gen.answer or "").strip()


def _dialog_history(state: dict[str, Any]) -> list[dict[str, str]]:
    history = [
        {"role": t["role"], "content": t["text"]}
        for t in (state.get("turns") or [])
        if t.get("role") in ("user", "assistant") and t.get("text")
    ][-8:]
    facts = [
        str(f).strip()
        for f in (state.get("learned_facts") or [])
        if str(f).strip()
    ][-8:]
    notes = [
        c.get("feedback", "").strip()
        for c in (state.get("corrections") or [])
        if (c.get("feedback") or "").strip()
    ][-5:]
    blocks: list[str] = []
    if facts:
        blocks.append("Известные факты по документу:\n" + "\n".join(f"- {f}" for f in facts))
    if notes:
        blocks.append("Учти исправления пользователя в этом диалоге:\n" + "\n".join(f"- {n}" for n in notes))
    if blocks:
        return [{"role": "system", "content": "\n\n".join(blocks)}] + history
    return history


def _last_assistant_text(state: dict[str, Any]) -> str:
    for turn in reversed(state.get("turns") or []):
        if turn.get("role") == "assistant" and turn.get("kind") != "system" and turn.get("text"):
            return str(turn["text"])
    return ""


def _record_stt_if_needed(
    *,
    raw_text: str | None,
    final_text: str,
    session_id: str,
    corpus_id: str,
) -> list[dict[str, str]]:
    raw = (raw_text or "").strip()
    final = (final_text or "").strip()
    if not raw or raw == final:
        return []
    from tmki_voice.stt_learn import record_stt_correction

    return record_stt_correction(
        raw,
        final,
        session_id=session_id,
        corpus_id=corpus_id,
        source="voice-doc",
    )


def process_turn(
    *,
    session_id: str,
    kind: TurnKind,
    text: str = "",
    raw_text: str | None = None,
    llm: str | None = None,
) -> dict[str, Any]:
    state = _load_session(session_id)
    if not state:
        raise ValueError("session not found")
    doc = state.get("document") or {}
    rel = doc.get("relative_path") or ""
    corpus = state.get("corpus_id") or "skru-2"
    model = (llm or state.get("llm") or "ollama").lower()
    state["llm"] = model
    citations = _doc_citations(corpus, rel) if rel else []
    history = _dialog_history(state)

    assistant_text = ""
    user_text = (text or "").strip()
    stt_learned: list[dict[str, str]] = []

    if kind == "user_question":
        if not user_text:
            raise ValueError("text required for user_question")
        stt_learned = _record_stt_if_needed(
            raw_text=raw_text,
            final_text=user_text,
            session_id=session_id,
            corpus_id=corpus,
        )
        turn: dict[str, Any] = {"role": "user", "kind": kind, "text": user_text, "at": _now()}
        if raw_text and raw_text.strip() != user_text:
            turn["raw_text"] = raw_text.strip()
        state["turns"].append(turn)
        assistant_text = _answer_voice_question(
            question=user_text,
            corpus_id=corpus,
            relative_path=rel,
            llm=model,
            history=history,
        )
        state["pending_ai_question"] = None

    elif kind == "ai_quiz":
        prompt = (
            "По фрагментам документа задай ОДИН короткий проверочный вопрос по-русски. "
            "Только вопрос, без ответа и без пояснений."
        )
        assistant_text = _llm_text(prompt=prompt, citations=citations, llm=model, history=history, mode="voice")
        assistant_text = assistant_text.strip().split("\n")[0].strip(" \"'")
        if assistant_text.endswith("?"):
            pass
        elif assistant_text:
            assistant_text = assistant_text.rstrip(".") + "?"
        state["pending_ai_question"] = assistant_text
        state["turns"].append({"role": "assistant", "kind": kind, "text": assistant_text, "at": _now()})

    elif kind == "user_answer":
        if not user_text:
            raise ValueError("text required for user_answer")
        pending = (state.get("pending_ai_question") or "").strip()
        stt_learned = _record_stt_if_needed(
            raw_text=raw_text,
            final_text=user_text,
            session_id=session_id,
            corpus_id=corpus,
        )
        turn = {"role": "user", "kind": kind, "text": user_text, "at": _now()}
        if raw_text and raw_text.strip() != user_text:
            turn["raw_text"] = raw_text.strip()
        state["turns"].append(turn)
        if pending:
            prompt = (
                f"Вопрос: {pending}\n"
                f"Ответ пользователя: {user_text}\n"
                "Кратко оцени (верно/частично/неверно) и поясни только по фрагментам. "
                "Без названия файла. 2–3 предложения."
            )
        else:
            prompt = (
                f"Реплика пользователя: {user_text}\n"
                "Ответь только по фрагментам, без названия файла. 2–3 предложения."
            )
        scoped = _voice_citations_for_question(corpus, rel, user_text or pending)
        use_citations = scoped if scoped else citations
        assistant_text = _strip_voice_boilerplate(
            _llm_text(prompt=prompt, citations=use_citations, llm=model, history=history, mode="voice")
        )
        state["pending_ai_question"] = None

    elif kind == "user_feedback":
        if not user_text:
            raise ValueError("text required for user_feedback")
        previous = _last_assistant_text(state)
        from tmki_voice.model_learn import record_model_feedback

        record_model_feedback(
            user_text,
            session_id=session_id,
            corpus_id=corpus,
            document_path=rel,
            previous_answer=previous,
        )
        correction = _parse_user_correction(user_text)
        state.setdefault("corrections", []).append(
            {
                "feedback": user_text,
                "correction": correction,
                "at": _now(),
                "previous_answer": previous[:500],
            }
        )
        if correction:
            state.setdefault("learned_facts", []).append(correction)
            state["learned_facts"] = state["learned_facts"][-20:]
        state["turns"].append(
            {"role": "user", "kind": kind, "text": user_text, "at": _now(), "feedback": True}
        )
        if correction:
            assistant_text = _strip_voice_boilerplate(correction)
        else:
            prompt = (
                f"Пользователь указал на ошибку: {user_text}\n"
                f"Твой предыдущий ответ: {previous or '—'}\n"
                "Дай исправленный ответ только по фрагментам. Без названия файла. 2–3 предложения."
            )
            scoped = _voice_citations_for_question(corpus, rel, user_text)
            use_citations = scoped if scoped else citations
            assistant_text = _strip_voice_boilerplate(
                _llm_text(
                    prompt=prompt,
                    citations=use_citations,
                    llm=model,
                    history=history,
                    mode="voice",
                )
            )
        state["pending_ai_question"] = None

    else:
        raise ValueError(f"unknown kind: {kind}")

    if kind != "ai_quiz":
        state["turns"].append(
            {"role": "assistant", "kind": kind, "text": assistant_text, "at": _now()}
        )

    _save_session(state)
    snap = get_session_snapshot(session_id)
    snap["assistant_text"] = assistant_text
    if user_text:
        snap["user_text"] = user_text
    snap["kind"] = kind
    if stt_learned:
        snap["stt_learned"] = stt_learned
    if kind == "user_feedback":
        snap["feedback_recorded"] = True
    snap["tts"] = synthesize_tts_payload(assistant_text)
    return snap


def synthesize_tts_payload(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {"provider": "none", "audio_base64": None}
    try:
        from tmki_voice import synthesize_speech

        result = synthesize_speech(text[:800])
        if result.audio_path and Path(result.audio_path).is_file():
            raw = Path(result.audio_path).read_bytes()
            try:
                Path(result.audio_path).unlink(missing_ok=True)
            except OSError:
                pass
            return {
                "provider": result.provider,
                "audio_base64": base64.b64encode(raw).decode("ascii"),
                "mime": "audio/wav",
            }
    except Exception as exc:
        return {"provider": "browser_fallback", "audio_base64": None, "error": str(exc)}
    return {"provider": "stub", "audio_base64": None}
