from __future__ import annotations

import json
import os
from typing import Any

from tmki_rag.embedding_providers import get_embedding_provider
from tmki_rag.embeddings import cosine_similarity
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

_PGVECTOR_EXT_SQL = "CREATE EXTENSION IF NOT EXISTS vector"

_ALTER_VECTOR_SQL = """
ALTER TABLE tmki_chunks
    ALTER COLUMN embedding TYPE vector({dims})
    USING embedding::vector({dims});
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
        use_pgvector: bool | None = None,
    ) -> None:
        super().__init__(dims=dims, embedding_provider=get_embedding_provider())
        self._conn = conn
        self._table = table
        self._use_pgvector = use_pgvector if use_pgvector is not None else False
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
            try:
                cur.execute(_PGVECTOR_EXT_SQL)
                cur.execute(_ALTER_VECTOR_SQL.format(dims=self._dims))
                self._use_pgvector = True
            except Exception:
                self._use_pgvector = False
        self._conn.commit()

    def add(self, chunks: list[dict[str, Any]]) -> int:
        count = 0
        with self._conn.cursor() as cur:
            for chunk in chunks:
                item = dict(chunk)
                self._ensure_embedding(item)
                emb = item["_embedding"]
                if self._use_pgvector:
                    emb_param = f"[{','.join(str(v) for v in emb)}]"
                    cur.execute(
                        f"""
                        INSERT INTO {self._table}
                        (chunk_id, doc_id, company_id, project_id, classification, payload, embedding, indexed_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s)
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
                            emb_param,
                            item["indexed_at"],
                        ),
                    )
                else:
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

    def count(self) -> int:
        with self._conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self._table}")
            row = cur.fetchone()
        return int(row[0]) if row else 0

    def create_ivfflat_index(self, *, lists: int | None = None) -> dict[str, Any]:
        """IVFFlat индекс после bulk load (pgvector). lists ≈ sqrt(n), min 100 rows."""
        if not self._use_pgvector:
            return {"status": "skipped", "reason": "pgvector_not_enabled"}
        n = self.count()
        if n < 100:
            return {"status": "skipped", "reason": "insufficient_rows", "row_count": n}
        idx_lists = lists or max(10, min(int(n**0.5), 1000))
        sql = (
            f"CREATE INDEX IF NOT EXISTS tmki_chunks_embedding_ivfflat "
            f"ON {self._table} USING ivfflat (embedding vector_cosine_ops) "
            f"WITH (lists = {idx_lists})"
        )
        with self._conn.cursor() as cur:
            cur.execute(sql)
        self._conn.commit()
        return {"status": "ok", "row_count": n, "lists": idx_lists}

    def bulk_add(self, chunks: list[dict[str, Any]], *, batch_size: int = 200) -> int:
        """Пакетная загрузка chunks (одна транзакция на batch)."""
        total = 0
        for offset in range(0, len(chunks), batch_size):
            batch = chunks[offset : offset + batch_size]
            total += self.add(batch)
        return total

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

    def search_similar(
        self,
        query: str,
        *,
        company_id: str,
        project_id: str,
        top_k: int = 20,
    ) -> list[tuple[float, dict[str, Any]]]:
        q_emb = self.embed_query(query)
        if self._use_pgvector:
            vec = f"[{','.join(str(v) for v in q_emb)}]"
            with self._conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT payload, 1 - (embedding <=> %s::vector) AS score
                    FROM {self._table}
                    WHERE company_id = %s AND project_id = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (vec, company_id, project_id, vec, top_k),
                )
                rows = cur.fetchall()
            result: list[tuple[float, dict[str, Any]]] = []
            for payload, score in rows:
                item = json.loads(payload) if isinstance(payload, str) else dict(payload)
                result.append((float(score), item))
            return result
        return super().search_similar(
            query,
            company_id=company_id,
            project_id=project_id,
            top_k=top_k,
        )
