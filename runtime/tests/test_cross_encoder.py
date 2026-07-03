import os

from tmki_rag.cross_encoder import available, rerank_results


def test_cross_encoder_rerank_preserves_order_without_model(monkeypatch):
    monkeypatch.setenv("TMKI_CROSS_ENCODER_RERANK", "1")
    results = [
        {
            "chunk_id": "a",
            "score": 0.5,
            "citation": {"snippet": "приказ о промышленной безопасности"},
        },
        {
            "chunk_id": "b",
            "score": 0.4,
            "citation": {"snippet": "инструктаж по охране труда"},
        },
    ]
    out = rerank_results("промбезопасность", results, top_k=2)
    assert len(out) <= 2
    if not available():
        assert out[0]["chunk_id"] == "a"


def test_feature_flags_defaults(monkeypatch):
    monkeypatch.delenv("TMKI_RAG_FUSION", raising=False)
    from tmki_rag.feature_flags import rag_fusion_enabled

    assert rag_fusion_enabled() is True
