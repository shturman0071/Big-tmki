#!/usr/bin/env python3
"""Экспорт ops bundle: dashboard + audit + quality + trend (read-only)."""

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
    parser = argparse.ArgumentParser(description="Export re-index ops bundle JSON")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--save", nargs="?", const=DEFAULT_STATE.parent / "reindex-ops-bundle-latest.json", type=Path)
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    from tmki_ingest.ops_bundle import build_ops_bundle

    bundle = build_ops_bundle(
        artifacts_dir=args.state.parent,
        state_path=args.state,
        heartbeat_path=args.heartbeat,
        lock_path=args.lock,
    )

    out_path = args.save
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.stdout:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
    elif out_path is not None:
        print(f"ops bundle saved: {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
