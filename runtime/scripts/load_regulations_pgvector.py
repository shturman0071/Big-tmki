#!/usr/bin/env python3
"""Загрузить regulations chunks.json в Postgres+pgvector и создать IVFFlat."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

DEFAULT_CHUNKS = None  # resolved in main()


def main() -> int:
    global DEFAULT_CHUNKS
    from tmki_rag.chunks_io import resolve_regulations_chunks_path

    DEFAULT_CHUNKS = resolve_regulations_chunks_path("auto")
    parser = argparse.ArgumentParser(description="Load regulations chunks into pgvector")
    parser.add_argument("--chunks", type=Path, default=None)
    parser.add_argument("--variant", choices=["auto", "v1", "v2"], default="auto")
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--ivfflat-lists", type=int, default=None)
    parser.add_argument("--skip-ivfflat", action="store_true")
    args = parser.parse_args()
    chunks_path = args.chunks or resolve_regulations_chunks_path(args.variant)

    if not chunks_path.is_file():
        print(f"chunks не найден: {chunks_path}", file=sys.stderr)
        return 1

    import os

    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL не задан", file=sys.stderr)
        return 1

    from tmki_rag.chunks_io import load_chunks_file
    from tmki_rag.pgvector import PgVectorChunkIndex

    chunks = load_chunks_file(chunks_path)
    print(f"Загрузка {len(chunks)} chunks из {chunks_path}")

    index = PgVectorChunkIndex.from_env()
    if not isinstance(index, PgVectorChunkIndex):
        print("PgVectorChunkIndex недоступен (psycopg/DATABASE_URL)", file=sys.stderr)
        return 1

    started = time.perf_counter()
    loaded = index.bulk_add(chunks, batch_size=args.batch_size)
    elapsed = time.perf_counter() - started
    print(f"Загружено: {loaded} за {elapsed:.1f}s, rows in DB: {index.count()}")

    if not args.skip_ivfflat:
        ivf = index.create_ivfflat_index(lists=args.ivfflat_lists)
        print(f"IVFFlat: {ivf}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
