#!/usr/bin/env python3
"""Экспорт master ops archive JSON."""

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
    parser = argparse.ArgumentParser(description="Export TMKI ops archive")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument(
        "--save",
        nargs="?",
        const=DEFAULT_STATE.parent / "tmki-ops-archive-latest.json",
        type=Path,
    )
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    from tmki_ingest.ops_archive import build_ops_archive

    archive = build_ops_archive(
        artifacts_dir=args.state.parent,
        state_path=args.state,
        heartbeat_path=args.heartbeat,
        lock_path=args.lock,
    )
    out_path = args.save or (args.state.parent / "tmki-ops-archive-latest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.stdout:
        print(json.dumps(archive, ensure_ascii=False, indent=2))
    else:
        print(f"ops archive saved: {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
