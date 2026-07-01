#!/usr/bin/env python3
"""Проверка готовности к finalize после re-index (read-only)."""

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
    parser = argparse.ArgumentParser(description="Preflight before finalize_regulations_index")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    from tmki_ingest.preflight_finalize import build_preflight_finalize

    out = build_preflight_finalize(
        state_path=args.state,
        heartbeat_path=args.heartbeat,
        lock_path=args.lock,
    )
    ok = bool(out["ready"])
    checks = out["checks"]

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("TMKI preflight finalize\n")
        for row in checks:
            tag = "ok" if row["ok"] else ("warn" if not row["blocking"] else "fail")
            print(f"  [{tag}] {row['name']}: {row['detail']}")
        print(f"\nready: {ok}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
