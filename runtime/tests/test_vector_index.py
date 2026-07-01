import os

from tmki_rag import ChunkIndex, VectorChunkIndex, get_chunk_index, hybrid_score_fn, rag_search, rag_search_with_index
from tmki_rag.search import _default_score


def test_vector_chunk_index_add_and_score():
    index = VectorChunkIndex()
    chunks = [
        {
            "chunk_id": "c1",
            "doc_id": "d1",
            "company_id": "co",
            "project_id": "pr",
            "classification": "internal",
            "content_preview": "маркшейдерская съёмка участка",
        }
    ]
    index.add(chunks)
    assert index.vector_score("маркшейдерская", chunks[0]) > 0


def test_hybrid_rag_search():
    index = VectorChunkIndex()
    chunk = {
        "chunk_id": "c1",
        "doc_id": "d1",
        "company_id": "company_tmki_ru",
        "project_id": "project_satimol",
        "department_id": "dept_markscheider",
        "classification": "restricted",
        "content_preview": "маркшейдерская съёмка на участке КС",
        "language": "ru",
        "page": 1,
        "start_offset": 0,
        "end_offset": 40,
    }
    index.add([chunk])
    score_fn = hybrid_score_fn(index, _default_score)
    resp = rag_search(
        {
            "trace_id": "t-vec",
            "query": "маркшейдерская съёмка",
            "policy_context": {
                "company_id": "company_tmki_ru",
                "project_id": "project_satimol",
                "department_id": "dept_markscheider",
                "clearance": "restricted",
            },
        },
        index.list(),
        score_fn=score_fn,
    )
    assert len(resp["results"]) >= 1


def test_get_chunk_index_defaults(monkeypatch):
    monkeypatch.delenv("TMKI_INDEX_BACKEND", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    index = get_chunk_index()
    assert isinstance(index, ChunkIndex)
    assert not isinstance(index, VectorChunkIndex)


def test_get_chunk_index_vector(monkeypatch):
    monkeypatch.setenv("TMKI_INDEX_BACKEND", "vector")
    index = get_chunk_index()
    assert isinstance(index, VectorChunkIndex)


def test_get_chunk_index_pgvector_fallback(monkeypatch):
    monkeypatch.setenv("TMKI_INDEX_BACKEND", "pgvector")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    index = get_chunk_index()
    assert isinstance(index, VectorChunkIndex)


def test_rag_search_with_index():
    index = VectorChunkIndex()
    chunk = {
        "chunk_id": "c1",
        "doc_id": "d1",
        "company_id": "company_tmki_ru",
        "project_id": "project_satimol",
        "department_id": "dept_markscheider",
        "classification": "restricted",
        "content_preview": "промбезопасность кран",
        "language": "ru",
        "page": 1,
        "start_offset": 0,
        "end_offset": 20,
    }
    index.add([chunk])
    resp = rag_search_with_index(
        {
            "trace_id": "t-idx",
            "query": "промбезопасность",
            "policy_context": {
                "company_id": "company_tmki_ru",
                "project_id": "project_satimol",
                "department_id": "dept_markscheider",
                "clearance": "restricted",
            },
            "top_k": 3,
        },
        index,
    )
    assert len(resp["results"]) >= 1
