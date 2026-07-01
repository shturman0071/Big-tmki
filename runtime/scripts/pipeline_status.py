#!/usr/bin/env python3
"""Единый статус pipeline re-index → finalize."""

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
    parser = argparse.ArgumentParser(description="TMKI pipeline status (re-index → finalize)")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    from tmki_ingest.pipeline_status import build_pipeline_status

    status = build_pipeline_status(
        artifacts_dir=args.state.parent,
        state_path=args.state,
        heartbeat_path=args.heartbeat,
        lock_path=args.lock,
    )

    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0

    ops = status["ops"]
    r = ops["report"]
    print("TMKI pipeline status\n")
    print(f"  phase: {status['phase']}")
    print(f"  progress: {r['live_progress']}/{r['total']} ({r['percent']}%)")
    if r.get("complete"):
        print("  re-index: complete")
    print(f"  chunks_v2: {r.get('chunks_v2')}  errors: {ops['errors']['errors_total']}")
    docker = status["docker"]
    print(f"  docker: {'ok' if docker['ready'] else 'not ready'} ({docker['detail']})")
    if ops.get("finalize_done"):
        print("  finalize: done")
    elif ops.get("ready_for_finalize"):
        print("  finalize: pending")
    arts = [k for k, v in status["artifacts"].items() if v]
    if arts:
        print(f"  artifacts: {', '.join(arts)}")
    print(f"\n  next: .\\scripts\\{status['next_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
