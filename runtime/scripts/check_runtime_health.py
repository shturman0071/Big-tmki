#!/usr/bin/env python3
"""Проверка готовности runtime-стека."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    ok = True
    print("TMKI runtime health check\n")

    try:
        import tmki_policy  # noqa: F401
        import tmki_rag  # noqa: F401
        import tmki_ingest  # noqa: F401
        import tmki_ocr  # noqa: F401
        print("  [ok] python packages")
    except ImportError as exc:
        print(f"  [fail] packages: {exc}")
        ok = False

    ocr_mode = os.environ.get("TMKI_OCR_MODE", "stub")
    print(f"  [info] TMKI_OCR_MODE={ocr_mode}")
    if ocr_mode == "local":
        try:
            import pypdf  # noqa: F401

            print("  [ok] pypdf installed")
        except ImportError:
            print("  [warn] pypdf missing — pip install -e '.[ocr]'")
    if ocr_mode == "http":
        for key in ("MINERU_API_URL", "MISTRAL_OCR_API_URL"):
            if os.environ.get(key):
                print(f"  [ok] {key}")
            else:
                print(f"  [warn] {key} not set")

    dsn = os.environ.get("DATABASE_URL", "")
    if dsn:
        try:
            import psycopg

            with psycopg.connect(dsn, connect_timeout=5) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            print("  [ok] DATABASE_URL")
        except Exception as exc:
            print(f"  [fail] DATABASE_URL: {exc}")
            ok = False
    else:
        print("  [info] DATABASE_URL not set")

    from tmki_rag.chunks_io import resolve_regulations_chunks_path

    try:
        chunks_path = resolve_regulations_chunks_path("auto")
        if chunks_path.is_file():
            print(f"  [ok] chunks: {chunks_path}")
        else:
            print("  [info] chunks file not found (run import/reindex)")
    except FileNotFoundError:
        print("  [info] chunks file not found")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
