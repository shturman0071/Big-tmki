#!/usr/bin/env python3
"""Единый dashboard мониторинга re-index (read-only)."""

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
DEFAULT_LOG = DEFAULT_STATE.parent / "reindex-progress-log.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-index operations dashboard")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--record-snapshot", action="store_true", help="Append progress snapshot before display")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    if args.record_snapshot:
        import subprocess

        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent / "record_reindex_snapshot.py"),
                "--state",
                str(args.state),
                "--heartbeat",
                str(args.heartbeat),
                "--lock",
                str(args.lock),
                "--log",
                str(args.log),
            ],
            env={**dict(__import__("os").environ), "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
        )
        if proc.returncode != 0:
            return proc.returncode

    from tmki_ingest.reindex_dashboard import build_reindex_dashboard

    dash = build_reindex_dashboard(
        state_path=args.state,
        heartbeat_path=args.heartbeat,
        lock_path=args.lock,
        progress_log_path=args.log,
    )

    if args.json:
        print(json.dumps(dash, ensure_ascii=False, indent=2))
        return 0

    ops = dash["ops"]
    r = ops["report"]
    ing = ops.get("ingest_stats") or {}
    err = ops.get("errors") or {}

    print("TMKI re-index dashboard\n")
    print(f"  progress: {r['live_progress']}/{r['total']} ({r['percent']}%)")
    if r.get("complete"):
        print("  status: complete")
    print(f"  imported: {ing.get('imported')}  chunks_v2: {ing.get('chunks_v2')}  errors: {err.get('errors_total', 0)}")
    if ing.get("import_yield_pct") is not None:
        print(f"  yield: {ing['import_yield_pct']}%  skip_temp: {ing.get('skip_temp')}  too_large: {ing.get('too_large')}")

    eta = dash.get("eta") or {}
    if eta.get("from_state_hours") is not None:
        print(f"  ETA (state): ~{eta['from_state_hours']} h")
    if eta.get("from_log_hours") is not None:
        print(f"  ETA (log): ~{eta['from_log_hours']} h")

    if ops.get("ready_for_finalize"):
        print("  ready_for_finalize: yes")
    elif ops.get("finalize_done"):
        print("  finalize: done")
    elif r.get("complete"):
        print("  ready_for_finalize: wait for lock release")

    ready_ms = r.get("milestone_ready")
    if ready_ms:
        print(f"  milestone ready: {ready_ms}% (optional)")
    elif r.get("next_milestone"):
        print(f"  next milestone: {r['next_milestone']}%")

    log_a = (dash.get("progress_log") or {}).get("analysis")
    if log_a and log_a.get("points"):
        print(f"  log points: {log_a['points']}  rate: {log_a.get('rate_per_hour')} files/h")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
