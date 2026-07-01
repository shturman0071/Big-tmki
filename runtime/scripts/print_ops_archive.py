#!/usr/bin/env python3
"""Печать текстовой сводки ops archive."""

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
DEFAULT_ARCHIVE = DEFAULT_STATE.parent / "tmki-ops-archive-latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Print ops archive summary")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--archive", type=Path, default=None)
    parser.add_argument("--save", type=Path, default=None)
    args = parser.parse_args()

    from tmki_ingest.ops_archive import build_ops_archive, format_ops_archive_summary

    if args.archive and args.archive.is_file():
        archive = json.loads(args.archive.read_text(encoding="utf-8"))
    elif DEFAULT_ARCHIVE.is_file():
        archive = json.loads(DEFAULT_ARCHIVE.read_text(encoding="utf-8"))
    elif args.state.is_file():
        archive = build_ops_archive(
            artifacts_dir=args.state.parent,
            state_path=args.state,
            heartbeat_path=args.heartbeat,
            lock_path=args.lock,
        )
    else:
        print("archive или state не найден", file=sys.stderr)
        return 1

    text = format_ops_archive_summary(archive)
    print(text)
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_text(text + "\n", encoding="utf-8")
        print(f"\nsaved: {args.save}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
