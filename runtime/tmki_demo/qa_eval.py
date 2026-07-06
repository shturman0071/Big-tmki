"""Онлайн-оценка Q→A по ground-truth (последовательно, с фиксацией ошибок)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = Path(__file__).resolve().parents[1]
GROUND_TRUTH = ROOT / "data" / "ground_truth"
STATE_PATH = RUNTIME / "artifacts" / "demo" / "qa-eval-state.json"
FAILURES_PATH = RUNTIME / "artifacts" / "demo" / "qa-eval-failures.json"

_SUITE_CACHE: dict[str, list[dict[str, Any]]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _suite_path(corpus_id: str) -> Path:
    if corpus_id == "skru-2":
        return GROUND_TRUTH / "skru2_qa.json"
    if corpus_id == "test_docs":
        return GROUND_TRUTH / "test_docs_qa.json"
    return GROUND_TRUTH / f"{corpus_id.replace('-', '_')}_qa.json"


def load_suite(corpus_id: str = "skru-2") -> list[dict[str, Any]]:
    if corpus_id in _SUITE_CACHE:
        return _SUITE_CACHE[corpus_id]
    path = _suite_path(corpus_id)
    if not path.is_file():
        _SUITE_CACHE[corpus_id] = []
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    tests = data.get("tests") or []
    _SUITE_CACHE[corpus_id] = tests
    return tests


def _hay(citation: dict[str, Any]) -> str:
    parts = [
        citation.get("file_name") or "",
        citation.get("relative_path") or "",
        citation.get("snippet") or "",
        citation.get("doc_id") or "",
    ]
    return " ".join(parts).lower()


def _citation_match(citations: list[dict[str, Any]], test: dict[str, Any]) -> tuple[bool, str]:
    needles = [n.lower() for n in (test.get("expect_any_in_citation") or [])]
    path_need = (test.get("expect_path_contains") or "").lower()
    digits = test.get("expect_digits") or []

    if not citations:
        return False, "нет цитат"

    if needles:
        found = False
        for cit in citations[:5]:
            hay = _hay(cit)
            if any(n in hay for n in needles):
                found = True
                break
        if not found:
            return False, f"нет ключей в топ-5: {', '.join(needles)}"

    if path_need:
        if not any(path_need in _hay(c) for c in citations[:5]):
            return False, f"путь не содержит «{path_need}»"

    if digits:
        from tmki_rag.match_score import filename_contains_doc_number

        top = citations[0]
        name = " ".join(str(top.get(k) or "") for k in ("file_name", "relative_path", "doc_id"))
        if not all(filename_contains_doc_number(name, d) for d in digits):
            return False, f"номер документа не совпал: {digits}"

    return True, "ok"


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


def _save_failures(failures: list[dict[str, Any]]) -> None:
    FAILURES_PATH.parent.mkdir(parents=True, exist_ok=True)
    FAILURES_PATH.write_text(
        json.dumps({"updated_at": _now(), "failures": failures}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def reset_eval(*, corpus_id: str = "skru-2") -> dict[str, Any]:
    state = {
        "corpus_id": corpus_id,
        "cursor": 0,
        "passed": 0,
        "failed": 0,
        "running": False,
        "transcript": [],
        "failures": [],
        "llm": "stub",
    }
    _save_state(state)
    _save_failures([])
    return get_eval_snapshot()


def get_eval_snapshot() -> dict[str, Any]:
    state = _load_state()
    corpus_id = state.get("corpus_id") or "skru-2"
    suite = load_suite(corpus_id)
    total = len(suite)
    cursor = int(state.get("cursor") or 0)
    return {
        "corpus_id": corpus_id,
        "total": total,
        "cursor": cursor,
        "passed": int(state.get("passed") or 0),
        "failed": int(state.get("failed") or 0),
        "done": cursor >= total,
        "running": bool(state.get("running")),
        "llm": state.get("llm") or "stub",
        "transcript": state.get("transcript") or [],
        "failures": state.get("failures") or [],
        "updated_at": state.get("updated_at"),
        "suite_path": str(_suite_path(corpus_id)),
    }


def _append_transcript(state: dict[str, Any], entry: dict[str, Any]) -> None:
    transcript: list[dict[str, Any]] = state.setdefault("transcript", [])
    transcript.append(entry)
    if len(transcript) > 80:
        state["transcript"] = transcript[-80:]


def run_one(
    *,
    corpus_id: str | None = None,
    llm: str = "stub",
) -> dict[str, Any]:
    from tmki_demo.qa import ask_regulations

    state = _load_state()
    if not state:
        state = reset_eval(corpus_id=corpus_id or "skru-2")
    corpus = corpus_id or state.get("corpus_id") or "skru-2"
    state["corpus_id"] = corpus
    state["llm"] = llm
    suite = load_suite(corpus)
    cursor = int(state.get("cursor") or 0)

    if cursor >= len(suite):
        state["running"] = False
        _save_state(state)
        return get_eval_snapshot()

    test = suite[cursor]
    state["running"] = True
    _save_state(state)

    _append_transcript(
        state,
        {
            "role": "question",
            "id": test.get("id"),
            "text": test.get("question"),
            "at": _now(),
        },
    )

    result = ask_regulations(test["question"], llm_provider=llm, corpus_id=corpus)
    citations = result.get("citations") or []
    answer = (result.get("answer") or "").strip()
    ok, reason = _citation_match(citations, test)

    answer_entry: dict[str, Any] = {
        "role": "answer",
        "id": test.get("id"),
        "text": answer[:1200],
        "reference": test.get("reference_answer"),
        "passed": ok,
        "reason": reason,
        "top_file": (citations[0].get("file_name") if citations else ""),
        "top_path": (citations[0].get("relative_path") if citations else ""),
        "at": _now(),
    }
    _append_transcript(state, answer_entry)

    if ok:
        state["passed"] = int(state.get("passed") or 0) + 1
    else:
        state["failed"] = int(state.get("failed") or 0) + 1
        failure = {
            "id": test.get("id"),
            "question": test.get("question"),
            "reference_answer": test.get("reference_answer"),
            "reason": reason,
            "answer": answer[:500],
            "top_file": answer_entry["top_file"],
            "top_path": answer_entry["top_path"],
            "at": _now(),
        }
        failures: list[dict[str, Any]] = state.setdefault("failures", [])
        failures.append(failure)
        _save_failures(failures)

    state["cursor"] = cursor + 1
    state["running"] = False
    _save_state(state)
    snap = get_eval_snapshot()
    snap["last"] = answer_entry
    return snap


def run_all(*, corpus_id: str = "skru-2", llm: str = "stub") -> dict[str, Any]:
    reset_eval(corpus_id=corpus_id)
    state = _load_state()
    state["llm"] = llm
    suite = load_suite(corpus_id)
    for _ in suite:
        run_one(corpus_id=corpus_id, llm=llm)
    return get_eval_snapshot()
