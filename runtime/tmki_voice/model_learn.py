"""Правки пользователя к ответам модели (голосовой диалог)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parents[1]
FEEDBACK_DB = RUNTIME / "artifacts" / "demo" / "model-corrections.json"
_MAX_EVENTS = 2000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_db() -> dict[str, Any]:
    if not FEEDBACK_DB.is_file():
        return {"events": []}
    try:
        data = json.loads(FEEDBACK_DB.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"events": []}
    data.setdefault("events", [])
    return data


def _save_db(data: dict[str, Any]) -> None:
    FEEDBACK_DB.parent.mkdir(parents=True, exist_ok=True)
    FEEDBACK_DB.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record_model_feedback(
    feedback: str,
    *,
    session_id: str | None = None,
    corpus_id: str | None = None,
    document_path: str | None = None,
    previous_answer: str | None = None,
    source: str = "voice-doc",
) -> dict[str, Any]:
    feedback = (feedback or "").strip()
    if not feedback:
        return {}

    event = {
        "at": _now(),
        "feedback": feedback,
        "session_id": session_id,
        "corpus_id": corpus_id,
        "document_path": document_path,
        "previous_answer": (previous_answer or "")[:2000],
        "source": source,
    }
    data = _load_db()
    events = data.setdefault("events", [])
    events.append(event)
    if len(events) > _MAX_EVENTS:
        data["events"] = events[-_MAX_EVENTS:]
    _save_db(data)
    return event


def list_model_feedback(limit: int = 50) -> dict[str, Any]:
    data = _load_db()
    events = list(reversed(data.get("events") or []))
    return {"total": len(events), "events": events[:limit]}
