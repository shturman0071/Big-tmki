#!/usr/bin/env python3
"""Проверка артефактов после finalize (read-only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_ARTIFACTS = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify post-finalize artifacts")
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.artifacts.is_dir():
        print(f"artifacts dir не найден: {args.artifacts}", file=sys.stderr)
        return 1

    from tmki_ingest.post_finalize_verify import build_post_finalize_verify

    out = build_post_finalize_verify(args.artifacts)
    ok = bool(out["verified"])

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("TMKI post-finalize verify\n")
        for row in out["checks"]:
            tag = "ok" if row["ok"] else ("warn" if not row["blocking"] else "fail")
            print(f"  [{tag}] {row['name']}: {row['detail']}")
        print(f"\nverified: {ok}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
