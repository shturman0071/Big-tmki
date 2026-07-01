#!/usr/bin/env python3
"""Статус re-index регламентов из reindex-state.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_STATE = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "reindex-state.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Show regulations re-index progress")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--total", type=int, default=10_089, help="Ожидаемое число ingest-кандидатов")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    state = json.loads(args.state.read_text(encoding="utf-8"))
    processed = state.get("processed", [])
    stats = state.get("stats", {})
    imported = stats.get("imported", 0)
    errors = stats.get("errors", 0)
    skip_temp = stats.get("skip_temp", 0)
    ocr_failed = stats.get("ocr_failed", 0)
    pct = 100.0 * len(processed) / args.total if args.total else 0.0

    chunks_v2 = args.state.parent / "chunks-v2.json"
    chunk_count = 0
    if chunks_v2.is_file():
        data = json.loads(chunks_v2.read_text(encoding="utf-8"))
        chunk_count = len(data.get("chunks", []))

    print(f"archive: {state.get('archive_root', '?')}")
    print(f"updated: {state.get('updated_at', '?')}")
    print(f"processed: {len(processed)}/{args.total} ({pct:.1f}%)")
    print(f"imported: {imported}  skip_temp: {skip_temp}  ocr_failed: {ocr_failed}  errors: {errors}")
    print(f"chunks-v2: {chunk_count} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
