import json

from tmki_rag.pgvector import PgVectorChunkIndex, _json_safe


def test_json_safe_strips_nul():
    dirty = {"content_preview": "test\u0000suffix", "nested": ["a\u0000b"]}
    clean = _json_safe(dirty)
    assert "\x00" not in clean["content_preview"]
    assert clean["nested"][0] == "ab"


class _MockCursor:
    def __init__(self, conn: "_MockConn") -> None:
        self._conn = conn
        self.rowcount = 0

    def execute(self, sql: str, params=None) -> None:
        self._conn.last_sql = sql
        self._conn.last_params = params
        if "DELETE FROM" in sql:
            self.rowcount = len(self._conn.inserts)
            self._conn.inserts.clear()
        if "INSERT INTO" in sql:
            self._conn.inserts.append(params)

    def fetchall(self):
        if self._conn.last_sql and "embedding <=>" in self._conn.last_sql:
            payload = json.dumps(
                {
                    "chunk_id": "c_pg",
                    "doc_id": "d1",
                    "company_id": "company_tmki_ru",
                    "project_id": "project_satimol",
                    "classification": "restricted",
                    "content_preview": "маркшейдерская съёмка",
                }
            )
            return [(payload, 0.91)]
        return []

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None


class _MockConn:
    def __init__(self) -> None:
        self.last_sql = ""
        self.last_params = None
        self.inserts: list = []

    def cursor(self) -> _MockCursor:
        return _MockCursor(self)

    def commit(self) -> None:
        pass


def test_pgvector_truncate_clears_rows():
    conn = _MockConn()
    index = PgVectorChunkIndex(conn, use_pgvector=True)
    index._chunks.append({"chunk_id": "c1"})
    conn.inserts.append(("row",))
    deleted = index.truncate()
    assert deleted == 1
    assert "DELETE FROM" in conn.last_sql
    assert index._chunks == []


def test_pgvector_search_similar_uses_cosine_sql():
    conn = _MockConn()
    index = PgVectorChunkIndex(conn, use_pgvector=True)
    results = index.search_similar(
        "маркшейдерская",
        company_id="company_tmki_ru",
        project_id="project_satimol",
        top_k=5,
    )
    assert "embedding <=>" in conn.last_sql
    assert len(results) == 1
    assert results[0][0] == 0.91
    assert results[0][1]["chunk_id"] == "c_pg"
