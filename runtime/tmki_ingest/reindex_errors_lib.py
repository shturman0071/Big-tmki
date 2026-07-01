"""Сводка ошибок re-index из state."""

from __future__ import annotations

from collections import Counter
from typing import Any


def error_key(msg: str) -> str:
    text = (msg or "").strip()
    if not text:
        return "unknown"
    return text.split(":", 1)[0][:80]


def summarize_errors(errors: list[dict[str, Any]], *, limit: int = 20) -> dict[str, Any]:
    counts = Counter(error_key(row.get("error", "")) for row in errors)
    return {
        "recent_count": len(errors),
        "summary": [{"type": key, "count": n} for key, n in counts.most_common()],
        "recent": errors[-limit:],
    }


def load_error_audit(state: dict[str, Any], *, limit: int = 20) -> dict[str, Any]:
    errors = state.get("recent_errors") or []
    stats = state.get("stats", {})
    total = int(stats.get("errors", len(errors)))
    return {
        "errors_total": total,
        **summarize_errors(errors, limit=limit),
    }
