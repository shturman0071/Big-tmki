from tmki_rag import VectorChunkIndex, hybrid_score_fn, rag_search_with_index
from tmki_rag.search import _default_score


def _chunk(doc_id: str, chunk_id: str, text: str) -> dict:
    return {
        "chunk_id": chunk_id,
        "doc_id": doc_id,
        "company_id": "company_tmki_ru",
        "project_id": "project_satimol",
        "department_id": "dept_markscheider",
        "classification": "restricted",
        "content_preview": text,
        "language": "ru",
        "page": 1,
        "start_offset": 0,
        "end_offset": len(text),
    }


def test_fulltext_finds_chunk_beyond_vector_top():
    index = VectorChunkIndex()
    filler = [_chunk("d0", f"c{i}", f"шумовой текст номер {i}") for i in range(30)]
    target = _chunk(
        "d_target",
        "c_target",
        "уникальная фраза про изоляцию кабельных линий на участке СКРУ",
    )
    index.add(filler + [target])
    score_fn = hybrid_score_fn(index, _default_score)
    resp = rag_search_with_index(
        {
            "trace_id": "t-full",
            "query": "изоляцию кабельных линий",
            "policy_context": {
                "company_id": "company_tmki_ru",
                "project_id": "project_satimol",
                "department_id": "dept_markscheider",
                "clearance": "restricted",
            },
            "top_k": 3,
        },
        index,
        score_fn=score_fn,
    )
    doc_ids = [r["doc_id"] for r in resp["results"]]
    assert "d_target" in doc_ids


def test_default_score_phrase_boost():
    chunk = {"content_preview": "требования к маркшейдерской съемке участка"}
    assert _default_score("маркшейдерской съемке", chunk) >= 0.9
