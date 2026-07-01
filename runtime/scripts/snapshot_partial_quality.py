#!/usr/bin/env python3
"""Partial quality benchmark на текущем chunks-v2 (read-only для re-index)."""

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
    parser = argparse.ArgumentParser(description="Partial v2 hybrid quality snapshot")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--save", type=Path, default=None)
    parser.add_argument("--label-percent", type=int, default=None, help="Имя файла quality-partial-p{N}.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    from tmki_ingest.partial_quality_benchmark import run_v2_hybrid_benchmark
    from tmki_ingest.quality_snapshot import write_partial_quality_snapshot
    from tmki_ingest.reindex_progress import build_reindex_report

    report = build_reindex_report(
        state_path=args.state,
        heartbeat_path=args.heartbeat,
        lock_path=args.lock,
    )
    if report.get("complete"):
        print("re-index завершён — используйте compare_chunks_quality / finalize", file=sys.stderr)
        return 2

    try:
        payload = run_v2_hybrid_benchmark()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    pct = args.label_percent if args.label_percent is not None else int(report.get("percent") or 0)
    out = args.save or (args.state.parent / f"quality-partial-p{pct}.json")
    latest = args.state.parent / "quality-partial-latest.json"
    write_partial_quality_snapshot(save_path=out, report=report, payload=payload)
    write_partial_quality_snapshot(save_path=latest, report=report, payload=payload)

    if args.json:
        print(json.dumps(json.loads(out.read_text(encoding="utf-8")), ensure_ascii=False, indent=2))
    else:
        print(f"partial quality saved: {out}", file=sys.stderr)
        print(f"  progress: {report['live_progress']}/{report['total']} ({report['percent']}%)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
