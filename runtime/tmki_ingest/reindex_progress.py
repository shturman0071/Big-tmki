"""Чтение прогресса re-index (state + heartbeat) для отчётов и wait-скриптов."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tmki_ingest.reindex_milestones import milestone_summary


def _parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def estimate_eta_hours(
    *,
    started: datetime | None,
    live_progress: int,
    total: int,
    now: datetime | None = None,
    min_elapsed_hours: float = 0.05,
) -> float | None:
    if total <= 0:
        return None
    if live_progress >= total:
        return 0.0
    if not started or live_progress <= 0:
        return None
    now = now or datetime.now(timezone.utc)
    elapsed_h = (now - started).total_seconds() / 3600.0
    if elapsed_h < min_elapsed_hours:
        return None
    rate = live_progress / elapsed_h
    if rate <= 0:
        return None
    return max(total - live_progress, 0) / rate


def build_reindex_report(
    *,
    state_path: Path,
    heartbeat_path: Path,
    lock_path: Path | None = None,
) -> dict[str, Any]:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    stats = state.get("stats", {})
    processed = len(state.get("processed", []))
    total = int(state.get("total_candidates") or 10_089)
    imported = int(stats.get("imported", 0))
    errors = int(stats.get("errors", 0))

    current_file = None
    hb_index = None
    if heartbeat_path.is_file():
        hb = json.loads(heartbeat_path.read_text(encoding="utf-8"))
        current_file = hb.get("current_file")
        hb_index = hb.get("file_index")

    live_progress = max(processed, int(hb_index or 0))
    pct = 100.0 * live_progress / total if total else 0.0
    complete = live_progress >= total

    chunk_count = 0
    chunks_path = state_path.parent / "chunks-v2.json"
    if chunks_path.is_file():
        chunk_count = len(json.loads(chunks_path.read_text(encoding="utf-8")).get("chunks", []))

    updated = _parse_iso(state.get("updated_at", ""))
    started = _parse_iso(state.get("started_at", "")) or updated
    eta_hours = estimate_eta_hours(started=started, live_progress=live_progress, total=total)

    recent_errors = state.get("recent_errors") or []
    milestones = milestone_summary(pct, state_path.parent / "milestones")

    lock_pid = None
    if lock_path and lock_path.is_file():
        from tmki_ingest.reindex_lock import process_alive, read_lock

        lk = read_lock(lock_path)
        if lk:
            pid = int(lk.get("pid") or 0)
            lock_pid = pid if process_alive(pid) else None

    return {
        "processed": processed,
        "live_progress": live_progress,
        "total": total,
        "percent": round(pct, 1),
        "complete": complete,
        "imported": imported,
        "chunks_v2": chunk_count,
        "errors": errors,
        "skip_temp": stats.get("skip_temp", 0),
        "ocr_failed": stats.get("ocr_failed", 0),
        "too_large": stats.get("too_large", 0),
        "current_file": current_file,
        "heartbeat_index": hb_index,
        "updated_at": state.get("updated_at"),
        "eta_hours": round(eta_hours, 1) if eta_hours is not None else None,
        "recent_errors_count": len(recent_errors),
        "lock_pid": lock_pid,
        **milestones,
    }
