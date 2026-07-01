#!/usr/bin/env python3
"""Сводный отчёт по re-index: прогресс, ETA, ошибки."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_STATE = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "reindex-state.json"
)
DEFAULT_HEARTBEAT = DEFAULT_STATE.parent / "reindex-heartbeat.json"
DEFAULT_LOCK = DEFAULT_STATE.parent / "reindex.lock"


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

    from tmki_ingest.reindex_progress import build_reindex_report

    report = build_reindex_report(
        state_path=args.state,
        heartbeat_path=args.heartbeat,
        lock_path=args.lock,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    live_progress = report["live_progress"]
    total = report["total"]
    pct = report["percent"]
    processed = report["processed"]
    imported = report["imported"]
    chunk_count = report["chunks_v2"]
    errors = report["errors"]
    eta_hours = report.get("eta_hours")
    milestones = {
        "milestones_done": report.get("milestones_done"),
        "milestone_ready": report.get("milestone_ready"),
        "next_milestone": report.get("next_milestone"),
    }
    current_file = report.get("current_file")
    hb_index = report.get("heartbeat_index")
    lock_pid = report.get("lock_pid")
    state_updated = report.get("updated_at")

    print("TMKI re-index report\n")
    print(f"  progress: {live_progress}/{total} ({pct:.1f}%)  [checkpoint {processed}]")
    if report.get("complete"):
        print("  status: complete")
    print(f"  imported: {imported}  chunks-v2: {chunk_count}")
    print(f"  errors: {errors}  skip_temp: {report.get('skip_temp', 0)}  ocr_failed: {report.get('ocr_failed', 0)}")
    if report.get("too_large"):
        print(f"  too_large: {report.get('too_large', 0)}")
    if eta_hours is not None:
        print(f"  ETA: ~{eta_hours:.1f} h")
    done = milestones.get("milestones_done") or []
    if done:
        print(f"  milestones done: {', '.join(str(m) for m in done)}%")
    ready = milestones.get("milestone_ready")
    if ready:
        print(f"  milestone ready: {ready}% — run .\\scripts\\reindex_milestone.ps1")
    elif milestones.get("next_milestone"):
        print(f"  next milestone: {milestones['next_milestone']}%")
    if current_file:
        print(f"  current: [{hb_index}/{total}] {current_file}")
    if lock_pid:
        print(f"  lock: pid={lock_pid} (active)")
    print(f"  checkpoint: {state_updated or '?'}")

    state = json.loads(args.state.read_text(encoding="utf-8"))
    recent_errors = state.get("recent_errors") or []
    if recent_errors:
        print(f"\n  recent errors ({len(recent_errors)}):")
        for row in recent_errors[-5:]:
            print(f"    - {row.get('path', '?')[:80]}")
            print(f"      {str(row.get('error', ''))[:120]}")
    return 0


from tmki_ingest.reindex_progress import estimate_eta_hours  # noqa: E402 — test compat

__all__ = ["estimate_eta_hours", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
