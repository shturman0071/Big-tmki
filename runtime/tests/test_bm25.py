from tmki_rag.bm25 import Bm25Index, reciprocal_rank_fusion


def _chunk(cid: str, text: str) -> dict:
    return {"chunk_id": cid, "content_preview": text}


def test_bm25_finds_exact_term():
    chunks = [
        _chunk("c1", "общие положения о безопасности"),
        _chunk("c2", "приказ Ростехнадзора 507 о промышленной безопасности"),
        _chunk("c3", "маркшейдерская съёмка участка"),
    ]
    idx = Bm25Index(chunks)
    if not idx.available:
        import pytest

        pytest.skip("rank_bm25 not installed")
    top = idx.top("приказ Ростехнадзора 507", top_k=3)
    assert top
    assert top[0][1]["chunk_id"] == "c2"


def test_bm25_lemmatized_case():
    # BM25 IDF требует корпус >2 документов, иначе термин "частый" → score 0.
    chunks = [
        _chunk("c1", "требования к договору подряда на объекте"),
        _chunk("c2", "погода на участке горных работ"),
        _chunk("c3", "инструкция по охране труда бригады"),
        _chunk("c4", "маркшейдерская съёмка опорной сети"),
    ]
    idx = Bm25Index(chunks)
    if not idx.available:
        import pytest

        pytest.skip("rank_bm25 not installed")
    top = idx.top("договоры", top_k=4)
    assert top
    assert top[0][1]["chunk_id"] == "c1"


def test_rrf_prefers_consensus():
    a = _chunk("a", "x")
    b = _chunk("b", "y")
    c = _chunk("c", "z")
    fused = reciprocal_rank_fusion([[a, b, c], [b, a, c]], top_k=3)
    assert fused[0]["chunk_id"] in {"a", "b"}
    assert fused[-1]["chunk_id"] == "c"
