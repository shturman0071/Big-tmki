"""Ручная QA-лаборатория: документ + вопрос + вердикт (форматы СКРУ-2)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tmki_rag.corpus_policy import resolve_corpus_archive

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = Path(__file__).resolve().parents[1]
GROUND_TRUTH = ROOT / "data" / "ground_truth"
STATE_PATH = RUNTIME / "artifacts" / "demo" / "qa-lab-state.json"
VERDICTS_PATH = RUNTIME / "artifacts" / "demo" / "qa-lab-verdicts.json"
SUITE_PATH = GROUND_TRUTH / "skru2_format_lab.json"

_VIEWABLE = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_archive_file(*, corpus_id: str, relative_path: str) -> Path | None:
    root = resolve_corpus_archive(corpus_id).resolve()
    rel = relative_path.replace("\\", "/").lstrip("/")
    if ".." in rel.split("/"):
        return None
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target if target.is_file() else None


def load_format_suite() -> list[dict[str, Any]]:
    if not SUITE_PATH.is_file():
        return []
    data = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    return list(data.get("tests") or [])


def _enrich_item(item: dict[str, Any], *, corpus_id: str) -> dict[str, Any]:
    rel = item.get("document_relative_path") or ""
    path = resolve_archive_file(corpus_id=corpus_id, relative_path=rel)
    fmt = (item.get("format") or Path(rel).suffix.lstrip(".")).lower()
    ext = f".{fmt}" if fmt and not fmt.startswith(".") else fmt
    out = dict(item)
    out["absolute_path"] = str(path) if path else None
    out["view_mode"] = "embed" if ext in _VIEWABLE else "external"
    out["exists"] = path is not None
    return out


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.is_file():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _save_verdicts(verdicts: list[dict[str, Any]]) -> None:
    VERDICTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    VERDICTS_PATH.write_text(
        json.dumps({"updated_at": _now(), "verdicts": verdicts}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _suite_fingerprint() -> str:
    if not SUITE_PATH.is_file():
        return ""
    try:
        data = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
        tests = data.get("tests") or []
        return f"{data.get('schema_version', '')}:{len(tests)}"
    except (OSError, json.JSONDecodeError):
        return ""


def _ensure_suite_current(state: dict[str, Any], *, corpus_id: str) -> None:
    fp = _suite_fingerprint()
    if state.get("suite_fingerprint") == fp and state.get("suite"):
        return
    suite = [_enrich_item(t, corpus_id=corpus_id) for t in load_format_suite()]
    state["suite"] = suite
    state["total"] = len(suite)
    state["suite_fingerprint"] = fp
    if int(state.get("cursor") or 0) >= len(suite):
        state["cursor"] = max(0, len(suite) - 1)


def _build_suite_list(
    suite: list[dict[str, Any]],
    *,
    cursor: int,
    verdicts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    verdict_map: dict[str, str] = {}
    for v in verdicts:
        vid = v.get("id")
        if vid:
            verdict_map[vid] = str(v.get("verdict") or "")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(suite):
        iid = item.get("id") or ""
        st = "current" if i == cursor else verdict_map.get(iid, "pending")
        out.append(
            {
                "index": i,
                "id": iid,
                "format": item.get("format"),
                "file_name": item.get("file_name"),
                "document_relative_path": item.get("document_relative_path"),
                "absolute_path": item.get("absolute_path"),
                "exists": item.get("exists"),
                "status": st,
            }
        )
    return out


def _lab_question_for(item: dict[str, Any]) -> str:
    """Вопрос по конкретному открытому файлу."""
    custom = (item.get("question") or "").strip()
    name = item.get("file_name") or Path(item.get("document_relative_path") or "").name
    fmt = (item.get("format") or "").upper()
    if custom and name.lower() in custom.lower():
        return custom
    return f"что в документе {name} ({fmt})"


def _with_lab_question(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if not item:
        return None
    out = dict(item)
    out["lab_question"] = _lab_question_for(item)
    return out


def reset_lab(*, corpus_id: str = "skru-2") -> dict[str, Any]:
    suite = [_enrich_item(t, corpus_id=corpus_id) for t in load_format_suite()]
    state = {
        "corpus_id": corpus_id,
        "cursor": 0,
        "total": len(suite),
        "suite": suite,
        "suite_fingerprint": _suite_fingerprint(),
        "current_answer": None,
        "verdicts": [],
        "stats": {"ok": 0, "fail": 0, "err": 0},
    }
    _save_state(state)
    _save_verdicts([])
    return get_lab_snapshot()


def get_lab_snapshot() -> dict[str, Any]:
    state = _load_state()
    if not state:
        return reset_lab()
    corpus = state.get("corpus_id") or "skru-2"
    _ensure_suite_current(state, corpus_id=corpus)
    _save_state(state)
    suite: list[dict[str, Any]] = state.get("suite") or []
    cursor = int(state.get("cursor") or 0)
    current = _with_lab_question(suite[cursor] if cursor < len(suite) else None)
    suite_list = _build_suite_list(suite, cursor=cursor, verdicts=state.get("verdicts") or [])
    return {
        "corpus_id": corpus,
        "cursor": cursor,
        "total": len(suite),
        "done": cursor >= len(suite),
        "current": current,
        "suite_list": suite_list,
        "current_answer": state.get("current_answer"),
        "verdicts": state.get("verdicts") or [],
        "stats": state.get("stats") or {"ok": 0, "fail": 0, "err": 0},
        "updated_at": state.get("updated_at"),
        "suite_path": str(SUITE_PATH),
    }


def ask_current(*, question: str | None = None, llm: str = "ollama") -> dict[str, Any]:
    from tmki_demo.qa import analyze_document, ask_regulations

    state = _load_state()
    if not state:
        reset_lab()
        state = _load_state()
    snap = get_lab_snapshot()
    current = snap.get("current")
    if not current:
        return snap
    q = (question or current.get("lab_question") or current.get("question") or "").strip()
    if not q:
        raise ValueError("question required")
    corpus = state.get("corpus_id") or "skru-2"
    rel = current.get("document_relative_path") or ""
    result: dict[str, Any]
    if rel:
        try:
            result = analyze_document(
                q,
                relative_path=rel,
                llm_provider=llm,
                corpus_id=corpus,
            )
        except Exception:
            result = ask_regulations(
                f"{q} {current.get('file_name') or ''}".strip(),
                llm_provider=llm,
                corpus_id=corpus,
            )
    else:
        result = ask_regulations(q, llm_provider=llm, corpus_id=corpus)
    state["current_answer"] = {
        "question": q,
        "answer": result.get("answer"),
        "citations": result.get("citations") or [],
        "confidence": result.get("confidence"),
        "llm_provider": result.get("llm_provider"),
        "document_file": current.get("file_name"),
        "document_path": rel,
        "asked_at": _now(),
    }
    _save_state(state)
    out = get_lab_snapshot()
    out["ask_result"] = state["current_answer"]
    return out


def record_verdict(*, verdict: str, note: str = "", reference_answer: str | None = None) -> dict[str, Any]:
    state = _load_state()
    if not state:
        return reset_lab()
    snap = get_lab_snapshot()
    current = snap.get("current")
    if not current:
        return snap
    vkey = verdict.strip().lower()
    if vkey not in ("ok", "fail", "err"):
        raise ValueError("verdict must be ok, fail, or err")
    ref = (reference_answer or current.get("reference_answer") or "").strip()
    cursor = int(state.get("cursor") or 0)
    suite: list[dict[str, Any]] = state.get("suite") or []
    if ref and cursor < len(suite):
        suite[cursor]["reference_answer"] = ref
    entry = {
        "id": current.get("id"),
        "format": current.get("format"),
        "file_name": current.get("file_name"),
        "document_relative_path": current.get("document_relative_path"),
        "question": (state.get("current_answer") or {}).get("question") or current.get("question"),
        "answer": (state.get("current_answer") or {}).get("answer"),
        "reference_answer": ref or None,
        "verdict": vkey,
        "note": note.strip(),
        "at": _now(),
    }
    verdicts: list[dict[str, Any]] = state.setdefault("verdicts", [])
    verdicts.append(entry)
    stats = state.setdefault("stats", {"ok": 0, "fail": 0, "err": 0})
    stats[vkey] = int(stats.get(vkey) or 0) + 1
    state["cursor"] = int(state.get("cursor") or 0) + 1
    state["current_answer"] = None
    _save_state(state)
    _save_verdicts(verdicts)
    return get_lab_snapshot()


def select_item(*, index: int | None = None, item_id: str | None = None) -> dict[str, Any]:
    state = _load_state()
    if not state:
        state = reset_lab()
    suite: list[dict[str, Any]] = state.get("suite") or []
    if not suite:
        return get_lab_snapshot()
    idx = int(index) if index is not None else -1
    if item_id:
        for i, item in enumerate(suite):
            if item.get("id") == item_id:
                idx = i
                break
    if idx < 0 or idx >= len(suite):
        raise ValueError("invalid document index")
    state["cursor"] = idx
    state["current_answer"] = None
    _save_state(state)
    snap = get_lab_snapshot()
    cur = snap.get("current")
    if cur and cur.get("view_mode") == "external" and cur.get("absolute_path"):
        snap["open_external"] = cur["absolute_path"]
    return snap


def get_files_list() -> dict[str, Any]:
    """Список файлов лаборатории (всегда актуальный, для колонки «Файлы»)."""
    state = _load_state()
    if not state:
        return reset_lab()
    corpus = state.get("corpus_id") or "skru-2"
    _ensure_suite_current(state, corpus_id=corpus)
    _save_state(state)
    suite: list[dict[str, Any]] = state.get("suite") or []
    cursor = int(state.get("cursor") or 0)
    return {
        "corpus_id": corpus,
        "cursor": cursor,
        "total": len(suite),
        "suite_list": _build_suite_list(suite, cursor=cursor, verdicts=state.get("verdicts") or []),
    }
