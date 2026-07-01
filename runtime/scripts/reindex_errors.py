#!/usr/bin/env python3
"""Последние ошибки re-index из reindex-state.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_STATE = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "reindex-state.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Show recent re-index errors")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    state = json.loads(args.state.read_text(encoding="utf-8"))
    errors = state.get("recent_errors") or []
    stats = state.get("stats", {})
    total = stats.get("errors", len(errors))

    print(f"errors total: {total}  (recent in state: {len(errors)})\n")
    for row in errors[-args.limit :]:
        print(f"  {row.get('path', '?')}")
        print(f"    {row.get('error', '')[:200]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
