#!/usr/bin/env python3
"""Детальная статистика ingest re-index (read-only)."""

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
    parser = argparse.ArgumentParser(description="Re-index ingest statistics")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    state = json.loads(args.state.read_text(encoding="utf-8"))
    from tmki_ingest.reindex_progress import build_reindex_report
    from tmki_ingest.reindex_stats import build_ingest_stats

    report = build_reindex_report(
        state_path=args.state,
        heartbeat_path=args.heartbeat,
        lock_path=args.lock,
    )
    stats = build_ingest_stats(state, report)

    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0

    print("TMKI re-index ingest stats\n")
    print(f"  live_scanned: {stats['live_scanned']}/{stats['total_candidates']}")
    print(f"  imported: {stats['imported']}  chunks_v2: {stats['chunks_v2']}")
    if stats.get("import_yield_pct") is not None:
        print(f"  import_yield: {stats['import_yield_pct']}%")
    print(
        f"  skip_temp: {stats['skip_temp']}  too_large: {stats['too_large']}  "
        f"ocr_failed: {stats['ocr_failed']}  errors: {stats['errors']}"
    )
    print(f"  pending_scan: {stats['pending_scan']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
