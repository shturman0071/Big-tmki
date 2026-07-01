#!/usr/bin/env python3
"""Сравнение partial quality snapshots (read-only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_ARTIFACTS = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare partial quality snapshots")
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from tmki_ingest.quality_trend import load_partial_quality_files, summarize_quality_trend

    snaps = load_partial_quality_files(args.artifacts)
    if not snaps:
        print(f"partial quality snapshots не найдены в {args.artifacts}", file=sys.stderr)
        return 1

    trend = summarize_quality_trend(snaps)
    if args.json:
        print(json.dumps(trend, ensure_ascii=False, indent=2))
        return 0

    print("TMKI partial quality trend\n")
    print(f"{'percent':>8} {'v2':>6} {'avg_score':>10}")
    print("-" * 28)
    for p in trend["points"]:
        print(f"{p.get('percent', 0):>7.1f}% {p.get('v2_count', 0):>6} {p.get('avg_score', 0):>10.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
