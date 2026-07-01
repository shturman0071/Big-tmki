"""Анализ JSONL лога прогресса re-index."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_progress_log(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def estimate_eta_hours_from_log(
    entries: list[dict[str, Any]],
    *,
    min_points: int = 2,
    now: datetime | None = None,
) -> float | None:
    """ETA по линейной скорости между первой и последней точкой лога."""
    if len(entries) < min_points:
        return None
    first, last = entries[0], entries[-1]
    t0 = _parse_iso(str(first.get("recorded_at", "")))
    t1 = _parse_iso(str(last.get("recorded_at", "")))
    if not t0 or not t1:
        return None
    p0 = int(first.get("live_progress") or 0)
    p1 = int(last.get("live_progress") or 0)
    if p1 <= p0:
        return None
    elapsed_h = (t1 - t0).total_seconds() / 3600.0
    if elapsed_h <= 0:
        return None
    rate = (p1 - p0) / elapsed_h
    if rate <= 0:
        return None
    total = int((last.get("ingest") or {}).get("total_candidates") or 0)
    if total <= 0:
        total = int((last.get("report") or {}).get("total") or 0)
    if total <= p1:
        return 0.0
    now = now or datetime.now(timezone.utc)
    # экстраполяция от последней точки
    last_dt = t1
    since_last_h = max((now - last_dt).total_seconds() / 3600.0, 0.0)
    projected = p1 + rate * since_last_h
    remaining = max(total - projected, 0)
    return remaining / rate


def analyze_progress_log(entries: list[dict[str, Any]], *, now: datetime | None = None) -> dict[str, Any]:
    if not entries:
        return {"points": 0, "eta_hours_from_log": None}
    first, last = entries[0], entries[-1]
    eta = estimate_eta_hours_from_log(entries, now=now)
    p0 = int(first.get("live_progress") or 0)
    p1 = int(last.get("live_progress") or 0)
    t0 = _parse_iso(str(first.get("recorded_at", "")))
    t1 = _parse_iso(str(last.get("recorded_at", "")))
    rate_per_hour = None
    if t0 and t1 and p1 > p0:
        elapsed_h = (t1 - t0).total_seconds() / 3600.0
        if elapsed_h > 0:
            rate_per_hour = round((p1 - p0) / elapsed_h, 1)
    return {
        "points": len(entries),
        "first_at": first.get("recorded_at"),
        "last_at": last.get("recorded_at"),
        "progress_delta": p1 - p0,
        "last_percent": last.get("percent"),
        "rate_per_hour": rate_per_hour,
        "eta_hours_from_log": round(eta, 2) if eta is not None else None,
    }
