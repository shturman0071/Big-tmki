"""Smoke-test pgvector backend (optional, requires running docker compose)."""

from __future__ import annotations

import os
import sys


def main() -> int:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        print("DATABASE_URL не задан. См. runtime/docker/env.example", file=sys.stderr)
        return 1

    os.environ.setdefault("TMKI_INDEX_BACKEND", "pgvector")
    os.environ.setdefault("TMKI_EMBEDDING_PROVIDER", "local")
    os.environ.setdefault("TMKI_EMBEDDING_DIMS", "64")

    try:
        from tmki_rag import get_chunk_index
    except ImportError:
        print("Запустите из runtime/ после pip install -e .", file=sys.stderr)
        return 1

    index = get_chunk_index()
    chunk = {
        "schema_version": "0.1",
        "chunk_id": "chunk_smoke_01",
        "doc_id": "doc_smoke",
        "company_id": "company_tmki_ru",
        "project_id": "project_satimol",
        "classification": "internal",
        "language": "ru",
        "page": 1,
        "start_offset": 0,
        "end_offset": 20,
        "embedding_model": "local-hash-v1",
        "content_preview": "smoke test pgvector",
        "indexed_at": "2026-07-01T12:00:00Z",
    }
    added = index.add([chunk])
    total = len(index.list())
    print(f"pgvector smoke OK: added={added}, total={total}, backend={type(index).__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
