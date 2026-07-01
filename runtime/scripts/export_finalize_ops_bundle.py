#!/usr/bin/env python3
"""Экспорт post-finalize ops bundle (read-only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_ARTIFACTS = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export post-finalize ops bundle JSON")
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument(
        "--save",
        nargs="?",
        const=DEFAULT_ARTIFACTS / "finalize-ops-bundle-latest.json",
        type=Path,
    )
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args()

    if not args.artifacts.is_dir():
        print(f"artifacts dir не найден: {args.artifacts}", file=sys.stderr)
        return 1

    from tmki_ingest.finalize_ops_bundle import build_finalize_ops_bundle

    bundle = build_finalize_ops_bundle(args.artifacts)
    out_path = args.save
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.stdout:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
    elif out_path is not None:
        print(f"finalize ops bundle saved: {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
