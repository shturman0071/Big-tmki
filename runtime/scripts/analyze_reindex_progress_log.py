#!/usr/bin/env python3
"""Анализ reindex-progress-log.jsonl: скорость и ETA (read-only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_LOG = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "reindex-progress-log.jsonl"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze re-index progress log")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from tmki_ingest.reindex_progress_log import analyze_progress_log, load_progress_log

    entries = load_progress_log(args.log)
    if not entries:
        print(f"log пуст или не найден: {args.log}", file=sys.stderr)
        return 1

    analysis = analyze_progress_log(entries)
    analysis["log_path"] = str(args.log)

    if args.json:
        print(json.dumps(analysis, ensure_ascii=False, indent=2))
        return 0

    print("TMKI progress log analysis\n")
    print(f"  points: {analysis['points']}")
    print(f"  progress_delta: {analysis['progress_delta']}")
    if analysis.get("rate_per_hour") is not None:
        print(f"  rate: {analysis['rate_per_hour']} files/h")
    if analysis.get("eta_hours_from_log") is not None:
        print(f"  ETA (from log): ~{analysis['eta_hours_from_log']} h")
    print(f"  last: {analysis.get('last_percent')}% @ {analysis.get('last_at')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
