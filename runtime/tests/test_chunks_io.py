import json
from pathlib import Path

import pytest

from tmki_rag.chunks_io import load_chunks_file, load_regulations_chunks
from tmki_rag.pgvector import PgVectorChunkIndex


def test_load_chunks_file(tmp_path: Path):
    path = tmp_path / "chunks.json"
    path.write_text(
        json.dumps({"chunks": [{"chunk_id": "c1", "content_preview": "test"}]}),
        encoding="utf-8",
    )
    chunks = load_chunks_file(path)
    assert len(chunks) == 1
    assert chunks[0]["chunk_id"] == "c1"


def test_load_regulations_chunks_missing():
    with pytest.raises(FileNotFoundError):
        load_regulations_chunks(Path("/nonexistent/chunks.json"))


def test_create_ivfflat_index_mock():
    class Cur:
        def __init__(self, conn):
            self.conn = conn

        def execute(self, sql):
            self.conn.last_sql = sql

        def fetchone(self):
            return (500,)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

    class Conn:
        def __init__(self):
            self.last_sql = ""

        def cursor(self):
            return Cur(self)

        def commit(self):
            pass

    conn = Conn()
    index = PgVectorChunkIndex(conn, use_pgvector=True)
    result = index.create_ivfflat_index(lists=50)
    assert result["status"] == "ok"
    assert "ivfflat" in conn.last_sql
