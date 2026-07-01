#!/usr/bin/env python3
"""Сводный отчёт по re-index: прогресс, ETA, ошибки."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_STATE = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "reindex-state.json"
)
DEFAULT_HEARTBEAT = DEFAULT_STATE.parent / "reindex-heartbeat.json"
DEFAULT_LOCK = DEFAULT_STATE.parent / "reindex.lock"
DEFAULT_CHUNKS = DEFAULT_STATE.parent / "chunks-v2.json"


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
    """ETA по live_progress (heartbeat) и started_at."""
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-index progress report")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    state = json.loads(args.state.read_text(encoding="utf-8"))
    stats = state.get("stats", {})
    processed = len(state.get("processed", []))
    total = int(state.get("total_candidates") or 10_089)
    imported = int(stats.get("imported", 0))
    errors = int(stats.get("errors", 0))

    current_file = None
    hb_index = None
    if args.heartbeat.is_file():
        hb = json.loads(args.heartbeat.read_text(encoding="utf-8"))
        current_file = hb.get("current_file")
        hb_index = hb.get("file_index")

    live_progress = max(processed, int(hb_index or 0))
    pct = 100.0 * live_progress / total if total else 0.0

    chunk_count = 0
    chunks_path = args.state.parent / "chunks-v2.json"
    if chunks_path.is_file():
        chunk_count = len(json.loads(chunks_path.read_text(encoding="utf-8")).get("chunks", []))

    updated = _parse_iso(state.get("updated_at", ""))
    started = _parse_iso(state.get("started_at", "")) or updated
    eta_hours = estimate_eta_hours(started=started, live_progress=live_progress, total=total)

    recent_errors = state.get("recent_errors") or []

    lock_pid = None
    if args.lock.is_file():
        from tmki_ingest.reindex_lock import process_alive, read_lock

        lk = read_lock(args.lock)
        if lk:
            pid = int(lk.get("pid") or 0)
            lock_pid = pid if process_alive(pid) else None

    report = {
        "processed": processed,
        "live_progress": live_progress,
        "total": total,
        "percent": round(pct, 1),
        "imported": imported,
        "chunks_v2": chunk_count,
        "errors": errors,
        "skip_temp": stats.get("skip_temp", 0),
        "ocr_failed": stats.get("ocr_failed", 0),
        "current_file": current_file,
        "heartbeat_index": hb_index,
        "updated_at": state.get("updated_at"),
        "eta_hours": round(eta_hours, 1) if eta_hours is not None else None,
        "recent_errors_count": len(recent_errors),
        "lock_pid": lock_pid,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print("TMKI re-index report\n")
    print(f"  progress: {live_progress}/{total} ({pct:.1f}%)  [checkpoint {processed}]")
    print(f"  imported: {imported}  chunks-v2: {chunk_count}")
    print(f"  errors: {errors}  skip_temp: {stats.get('skip_temp', 0)}  ocr_failed: {stats.get('ocr_failed', 0)}")
    if eta_hours is not None:
        print(f"  ETA: ~{eta_hours:.1f} h")
    if current_file:
        print(f"  current: [{hb_index}/{total}] {current_file}")
    if lock_pid:
        print(f"  lock: pid={lock_pid} (active)")
    print(f"  checkpoint: {state.get('updated_at', '?')}")
    if recent_errors:
        print(f"\n  recent errors ({len(recent_errors)}):")
        for row in recent_errors[-5:]:
            print(f"    - {row.get('path', '?')[:80]}")
            print(f"      {str(row.get('error', ''))[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
