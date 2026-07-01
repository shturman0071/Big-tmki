#!/usr/bin/env python3
"""Записать snapshot прогресса re-index в JSONL (read-only для re-index процесса)."""

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
DEFAULT_LOG = DEFAULT_STATE.parent / "reindex-progress-log.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description="Append re-index progress snapshot to JSONL log")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    state = json.loads(args.state.read_text(encoding="utf-8"))
    from tmki_ingest.reindex_ops import build_ops_status
    from tmki_ingest.reindex_stats import build_ingest_stats

    status = build_ops_status(
        state_path=args.state,
        heartbeat_path=args.heartbeat,
        lock_path=args.lock,
    )
    ingest = build_ingest_stats(state, status["report"])
    row = {
        "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "percent": status["report"].get("percent"),
        "live_progress": status["report"].get("live_progress"),
        "complete": status["report"].get("complete"),
        "ingest": ingest,
        "ready_for_finalize": status.get("ready_for_finalize"),
    }

    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"snapshot: {row['live_progress']} ({row['percent']}%) -> {args.log}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
