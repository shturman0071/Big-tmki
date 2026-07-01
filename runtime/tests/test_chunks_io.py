import json
from pathlib import Path

import pytest

from tmki_rag.chunks_io import (
    DEFAULT_REGULATIONS_CHUNKS,
    DEFAULT_REGULATIONS_CHUNKS_V2,
    load_chunks_file,
    load_regulations_chunks,
    resolve_regulations_chunks_path,
)
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


def test_resolve_prefers_v2(tmp_path: Path, monkeypatch):
    v1 = tmp_path / "chunks.json"
    v2 = tmp_path / "chunks-v2.json"
    v1.write_text('{"chunks":[]}', encoding="utf-8")
    v2.write_text('{"chunks":[]}', encoding="utf-8")
    monkeypatch.setattr("tmki_rag.chunks_io.DEFAULT_REGULATIONS_CHUNKS", v1)
    monkeypatch.setattr("tmki_rag.chunks_io.DEFAULT_REGULATIONS_CHUNKS_V2", v2)
    assert resolve_regulations_chunks_path("auto") == v2
    assert resolve_regulations_chunks_path("v1") == v1


def test_resolve_v1_only(tmp_path: Path, monkeypatch):
    v1 = tmp_path / "chunks.json"
    v2 = tmp_path / "chunks-v2.json"
    v1.write_text('{"chunks":[]}', encoding="utf-8")
    monkeypatch.setattr("tmki_rag.chunks_io.DEFAULT_REGULATIONS_CHUNKS", v1)
    monkeypatch.setattr("tmki_rag.chunks_io.DEFAULT_REGULATIONS_CHUNKS_V2", v2)
    assert resolve_regulations_chunks_path("auto") == v1


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


def test_pgvector_incremental_slice(tmp_path: Path):
    from tmki_rag.pgvector_sync import (
        save_pgvector_sync_state,
        slice_chunks_for_incremental,
        sync_state_path,
    )

    chunks_path = tmp_path / "chunks-v2.json"
    chunks_path.write_text("{}", encoding="utf-8")
    state_path = sync_state_path(chunks_path)
    all_chunks = [{"chunk_id": f"c{i}"} for i in range(5)]
    save_pgvector_sync_state(
        state_path,
        variant="v2",
        chunks_path=chunks_path,
        loaded_count=3,
    )
    new_chunks, offset = slice_chunks_for_incremental(
        all_chunks,
        variant="v2",
        chunks_path=chunks_path,
        state_path=state_path,
    )
    assert offset == 3
    assert len(new_chunks) == 2
    assert new_chunks[0]["chunk_id"] == "c3"
