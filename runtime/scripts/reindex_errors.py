#!/usr/bin/env python3
"""Последние ошибки re-index из reindex-state.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tmki_ingest.reindex_errors_lib import load_error_audit

DEFAULT_STATE = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "reindex-state.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Show recent re-index errors")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--summary", action="store_true", help="Группировка по типу ошибки")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    state = json.loads(args.state.read_text(encoding="utf-8"))
    audit = load_error_audit(state, limit=args.limit)
    errors = audit["recent"]

    if args.json:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
        return 0

    print(f"errors total: {audit['errors_total']}  (recent in state: {audit['recent_count']})\n")

    if args.summary and audit["summary"]:
        print("summary:")
        for row in audit["summary"]:
            print(f"  {row['count']:>3}  {row['type']}")
        print()

    for row in errors:
        print(f"  {row.get('path', '?')}")
        print(f"    {row.get('error', '')[:200]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
