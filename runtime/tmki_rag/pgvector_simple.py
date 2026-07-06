"""pgvector-индекс для таблицы chunks (root reindex_all.py, 768-dim Ollama embeddings)."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any

from tmki_rag.embedding_providers import get_embedding_provider
from tmki_rag.vector import VectorChunkIndex

def _demo_company_id() -> str:
    return os.environ.get("TMKI_DEMO_COMPANY_ID", "company_tmki_ru").strip() or "company_tmki_ru"


def _demo_project_id() -> str:
    return os.environ.get("TMKI_DEMO_PROJECT_ID", "project_satimol").strip() or "project_satimol"


def _demo_department_id() -> str | None:
    raw = os.environ.get("TMKI_DEMO_DEPARTMENT_ID", "dept_markscheider").strip()
    return raw or None


_DEMO_CLASSIFICATION = "internal"


def _parse_embedding(raw: Any) -> list[float]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [float(x) for x in raw]
    text = str(raw).strip()
    if text.startswith("[") and text.endswith("]"):
        return [float(x) for x in text[1:-1].split(",") if x.strip()]
    return []


def _row_to_chunk(row: tuple) -> dict[str, Any]:
    (
        chunk_id,
        doc_id,
        doc_path,
        content,
        page,
        section,
        metadata_raw,
    ) = row
    metadata: dict[str, Any] = {}
    if metadata_raw:
        if isinstance(metadata_raw, dict):
            metadata = metadata_raw
        else:
            try:
                metadata = json.loads(metadata_raw)
            except (TypeError, json.JSONDecodeError):
                metadata = {}
    rel = (doc_path or metadata.get("doc_path") or doc_id or "").replace("\\", "/")
    file_name = os.path.basename(rel) if rel else str(doc_id or chunk_id)
    dept = metadata.get("department_id") or _demo_department_id()
    return {
        "chunk_id": chunk_id,
        "doc_id": doc_id or file_name,
        "company_id": metadata.get("company_id") or _demo_company_id(),
        "project_id": metadata.get("project_id") or _demo_project_id(),
        "department_id": dept,
        "classification": metadata.get("classification") or _DEMO_CLASSIFICATION,
        "content_preview": content or "",
        "source_relative_path": rel,
        "file_name": file_name,
        "page": page,
        "section": section,
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }


class SimpleChunksPgIndex(VectorChunkIndex):
    """Чтение плоской таблицы chunks (content + vector embedding)."""

    def __init__(self, conn: Any, *, dims: int, table: str = "chunks", dsn: str = "") -> None:
        super().__init__(dims=dims, embedding_provider=get_embedding_provider())
        self._conn = conn
        self._dsn = dsn
        self._table = table
        self._loaded = False
        self._lock = threading.RLock()

    def _ensure_conn(self) -> None:
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1")
        except Exception:
            dsn = self._dsn or os.environ.get("DATABASE_URL", "").strip()
            if not dsn:
                raise
            import psycopg2

            self._conn = psycopg2.connect(dsn)
            self._loaded = False

    @classmethod
    def from_env(cls) -> "SimpleChunksPgIndex | None":
        dsn = os.environ.get("DATABASE_URL", "").strip()
        if not dsn:
            return None
        table = os.environ.get("TMKI_PGVECTOR_TABLE", "chunks").strip() or "chunks"
        dims = int(os.environ.get("TMKI_EMBEDDING_DIMS", os.environ.get("TMKI_EMBEDDING_DIM", "768")))
        try:
            import psycopg2

            conn = psycopg2.connect(dsn)
        except ImportError:
            try:
                import psycopg

                conn = psycopg.connect(dsn)
            except ImportError:
                return None
        except Exception:
            return None
        index = cls(conn, dims=dims, table=table, dsn=dsn)
        return index

    def count(self) -> int:
        with self._lock:
            self._ensure_conn()
            with self._conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {self._table}")
                row = cur.fetchone()
            return int(row[0]) if row else 0

    def count_for_corpus(self, corpus_id: str | None) -> int:
        with self._lock:
            self._ensure_conn()
            with self._conn.cursor() as cur:
                if corpus_id:
                    cur.execute(
                        f"SELECT COUNT(*) FROM {self._table} WHERE corpus_id = %s",
                        (corpus_id,),
                    )
                else:
                    cur.execute(f"SELECT COUNT(*) FROM {self._table}")
                row = cur.fetchone()
            return int(row[0]) if row else 0

    def _load_rows(self) -> None:
        with self._lock:
            if self._loaded:
                return
            self._ensure_conn()
            sql = f"""
                SELECT chunk_id, doc_id, doc_path, content, page, section, metadata
                FROM {self._table}
                WHERE content IS NOT NULL
            """
            with self._conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            chunks: list[dict[str, Any]] = []
            for row in rows:
                item = _row_to_chunk(row)
                with self._conn.cursor() as cur:
                    cur.execute(
                        f"SELECT embedding::text FROM {self._table} WHERE chunk_id = %s",
                        (item["chunk_id"],),
                    )
                    emb_row = cur.fetchone()
                item["_embedding"] = _parse_embedding(emb_row[0] if emb_row else None)
                chunks.append(item)
            self._chunks = chunks
            self._loaded = True

    def list(self) -> list[dict[str, Any]]:
        self._load_rows()
        return super().list()

    def search_similar(
        self,
        query: str,
        *,
        company_id: str,
        project_id: str,
        top_k: int = 20,
        corpus_id: str | None = None,
    ) -> list[tuple[float, dict[str, Any]]]:
        with self._lock:
            self._ensure_conn()
            q_emb = self.embed_query(query)
            vec = f"[{','.join(str(v) for v in q_emb)}]"
            limit = top_k
            env_top = os.environ.get("TMKI_RAG_TOP_K")
            if env_top:
                try:
                    limit = int(env_top)
                except ValueError:
                    pass
            corpus_filter = corpus_id or os.environ.get("TMKI_ACTIVE_CORPUS", "").strip() or None
            sql = f"""
                SELECT chunk_id, doc_id, doc_path, content, page, section, metadata,
                       1 - (embedding <=> %s::vector) AS score
                FROM {self._table}
                WHERE embedding IS NOT NULL
            """
            params: list[Any] = [vec]
            if corpus_filter:
                sql += " AND corpus_id = %s"
                params.append(corpus_filter)
            sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
            params.extend([vec, limit])
            with self._conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
            result: list[tuple[float, dict[str, Any]]] = []
            for row in rows:
                item = _row_to_chunk(row[:7])
                item["_embedding"] = q_emb  # placeholder; score from DB
                result.append((float(row[7]), item))
            return result
