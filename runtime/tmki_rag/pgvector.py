from __future__ import annotations

import json
import os
from typing import Any

from tmki_rag.embeddings import text_embedding
from tmki_rag.vector import VectorChunkIndex

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS tmki_chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    classification TEXT NOT NULL,
    payload JSONB NOT NULL,
    embedding DOUBLE PRECISION[] NOT NULL,
    indexed_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS tmki_chunks_project_idx ON tmki_chunks (company_id, project_id);
"""


class PgVectorChunkIndex(VectorChunkIndex):
    """
    PostgreSQL + pgvector backend (optional psycopg).
    Без DATABASE_URL или psycopg — fallback на in-memory VectorChunkIndex.
    """

    def __init__(
        self,
        conn: Any,
        *,
        dims: int = 64,
        table: str = "tmki_chunks",
    ) -> None:
        super().__init__(dims=dims)
        self._conn = conn
        self._table = table
        self._ensure_schema()

    @classmethod
    def from_env(cls) -> VectorChunkIndex:
        dsn = os.environ.get("DATABASE_URL", "")
        if not dsn:
            return VectorChunkIndex()
        try:
            import psycopg
        except ImportError:
            return VectorChunkIndex()
        conn = psycopg.connect(dsn)
        return cls(conn)

    def _ensure_schema(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute(_CREATE_SQL)
        self._conn.commit()

    def add(self, chunks: list[dict[str, Any]]) -> int:
        count = 0
        with self._conn.cursor() as cur:
            for chunk in chunks:
                item = dict(chunk)
                emb = text_embedding(item.get("content_preview", ""), dims=self._dims)
                item["_embedding"] = emb
                cur.execute(
                    f"""
                    INSERT INTO {self._table}
                    (chunk_id, doc_id, company_id, project_id, classification, payload, embedding, indexed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        payload = EXCLUDED.payload,
                        embedding = EXCLUDED.embedding,
                        indexed_at = EXCLUDED.indexed_at
                    """,
                    (
                        item["chunk_id"],
                        item["doc_id"],
                        item["company_id"],
                        item["project_id"],
                        item["classification"],
                        json.dumps(item),
                        emb,
                        item["indexed_at"],
                    ),
                )
                count += 1
                self._chunks.append(item)
        self._conn.commit()
        return count

    def list(self) -> list[dict[str, Any]]:
        if self._chunks:
            return super().list()
        rows: list[dict[str, Any]] = []
        with self._conn.cursor() as cur:
            cur.execute(f"SELECT payload FROM {self._table} ORDER BY indexed_at")
            for (payload,) in cur.fetchall():
                if isinstance(payload, str):
                    rows.append(json.loads(payload))
                else:
                    rows.append(dict(payload))
        self._chunks = rows
        return super().list()
