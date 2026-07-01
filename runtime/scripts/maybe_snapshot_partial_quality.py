#!/usr/bin/env python3
"""Partial quality snapshot только при достижении порога (75/80/85/90/95%)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_STATE = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "reindex-state.json"
)
DEFAULT_HEARTBEAT = DEFAULT_STATE.parent / "reindex-heartbeat.json"
DEFAULT_LOCK = DEFAULT_STATE.parent / "reindex.lock"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scheduled partial quality snapshot")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    from tmki_ingest.partial_quality_benchmark import run_v2_hybrid_benchmark
    from tmki_ingest.quality_snapshot_schedule import try_scheduled_partial_snapshot

    try:
        threshold = try_scheduled_partial_snapshot(
            state_path=args.state,
            heartbeat_path=args.heartbeat,
            lock_path=args.lock,
            run_benchmark=run_v2_hybrid_benchmark,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if threshold is None:
        if not args.quiet:
            print("no scheduled snapshot due", file=sys.stderr)
        return 0

    out = args.state.parent / f"quality-partial-p{threshold}.json"
    if not args.quiet:
        print(f"partial quality saved: {out} (threshold {threshold}%)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
