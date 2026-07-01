#!/usr/bin/env python3
"""Ожидание 100% re-index (read-only poll, не запускает re-index)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

DEFAULT_STATE = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "reindex-state.json"
)
DEFAULT_HEARTBEAT = DEFAULT_STATE.parent / "reindex-heartbeat.json"
DEFAULT_LOCK = DEFAULT_STATE.parent / "reindex.lock"


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait until re-index reaches 100%")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--poll-seconds", type=int, default=120)
    parser.add_argument("--json", action="store_true", help="Вывести финальный отчёт JSON и выйти")
    parser.add_argument("--once", action="store_true", help="Один опрос: exit 0 если complete, иначе 2")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    from tmki_ingest.reindex_progress import build_reindex_report

    while True:
        report = build_reindex_report(
            state_path=args.state,
            heartbeat_path=args.heartbeat,
            lock_path=args.lock,
        )
        if report["complete"]:
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                print(
                    f"re-index complete: {report['live_progress']}/{report['total']} "
                    f"chunks={report['chunks_v2']} errors={report['errors']}",
                    file=sys.stderr,
                )
            return 0

        if args.once:
            print(
                f"in progress: {report['live_progress']}/{report['total']} ({report['percent']}%)",
                file=sys.stderr,
            )
            return 2

        eta = report.get("eta_hours")
        eta_s = f" ETA ~{eta}h" if eta is not None else ""
        print(
            f"[wait] {report['live_progress']}/{report['total']} ({report['percent']}%){eta_s}",
            file=sys.stderr,
        )
        time.sleep(max(args.poll_seconds, 5))


if __name__ == "__main__":
    raise SystemExit(main())
