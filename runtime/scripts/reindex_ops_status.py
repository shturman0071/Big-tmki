#!/usr/bin/env python3
"""Единый ops-статус re-index (read-only)."""

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
    parser = argparse.ArgumentParser(description="Re-index operations status")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    from tmki_ingest.reindex_ops import build_ops_status

    status = build_ops_status(
        state_path=args.state,
        heartbeat_path=args.heartbeat,
        lock_path=args.lock,
    )

    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0

    r = status["report"]
    print("TMKI re-index ops status\n")
    print(f"  progress: {r['live_progress']}/{r['total']} ({r['percent']}%)")
    if r.get("complete"):
        print("  status: complete")
    print(f"  chunks-v2: {r.get('chunks_v2')}  errors: {status['errors']['errors_total']}")
    if status["ready_for_finalize"]:
        print("  ready_for_finalize: yes")
    elif r.get("complete"):
        print("  ready_for_finalize: wait for lock release")
    if status["finalize_done"]:
        print("  finalize: done")
    elif status["ready_for_finalize"]:
        print("  finalize: pending — run .\\scripts\\wait_and_finalize.ps1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
