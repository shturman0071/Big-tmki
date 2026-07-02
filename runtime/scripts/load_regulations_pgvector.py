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
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Очистить pgvector и загрузить chunks заново (после изменения документов)",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Загрузить только новые chunks с прошлого sync (pgvector-sync-state.json)",
    )
    args = parser.parse_args()
    if args.replace and args.incremental:
        print("Нельзя одновременно --replace и --incremental", file=sys.stderr)
        return 1

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
    from tmki_rag.pgvector_sync import (
        save_pgvector_sync_state,
        slice_chunks_for_incremental,
        sync_state_path,
    )

    all_chunks = load_chunks_file(chunks_path)
    offset = 0
    chunks = all_chunks
    if args.incremental:
        chunks, offset = slice_chunks_for_incremental(
            all_chunks,
            variant=args.variant,
            chunks_path=chunks_path,
            state_path=sync_state_path(chunks_path),
        )
        if not chunks:
            print(f"Нет новых chunks (всего {len(all_chunks)}, уже загружено {offset})")
            return 0
        print(f"Incremental: {len(chunks)} новых chunks (offset {offset}, всего {len(all_chunks)})")
    else:
        print(f"Загрузка {len(chunks)} chunks из {chunks_path}")

    index = PgVectorChunkIndex.from_env()
    if not isinstance(index, PgVectorChunkIndex):
        print("PgVectorChunkIndex недоступен (psycopg/DATABASE_URL)", file=sys.stderr)
        return 1

    state_file = sync_state_path(chunks_path)
    if args.replace:
        deleted = index.truncate()
        if state_file.is_file():
            state_file.unlink()
        print(f"pgvector очищен: удалено {deleted} строк, загружаем {len(chunks)} chunks")

    started = time.perf_counter()
    loaded = index.bulk_add(chunks, batch_size=args.batch_size)
    elapsed = time.perf_counter() - started
    print(f"Загружено: {loaded} за {elapsed:.1f}s, rows in DB: {index.count()}")

    if args.incremental or loaded:
        save_pgvector_sync_state(
            sync_state_path(chunks_path),
            variant=args.variant,
            chunks_path=chunks_path,
            loaded_count=offset + loaded if args.incremental else len(all_chunks),
        )

    if not args.skip_ivfflat:
        ivf = index.create_ivfflat_index(lists=args.ivfflat_lists)
        print(f"IVFFlat: {ivf}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
