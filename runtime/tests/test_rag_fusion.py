from tmki_rag.rag_fusion import expand_query_variants, fuse_chunk_rankings
from tmki_rag.bm25 import reciprocal_rank_fusion


def _chunk(cid: str, text: str) -> dict:
    return {"chunk_id": cid, "content_preview": text}


def test_expand_query_variants_includes_original():
    variants = expand_query_variants("требования к армированию лестниц")
    assert variants
    assert variants[0] == "требования к армированию лестниц"
    assert len(variants) >= 2


def test_fuse_chunk_rankings_rrf():
    a, b, c = _chunk("a", "alpha"), _chunk("b", "beta"), _chunk("c", "gamma")
    fused = fuse_chunk_rankings([[a, b], [b, a, c]], top_k=3)
    assert fused[0]["chunk_id"] in {"a", "b"}


def test_reciprocal_rank_fusion_stable():
    items = [_chunk(f"c{i}", f"t{i}") for i in range(5)]
    out = reciprocal_rank_fusion([items, list(reversed(items))], top_k=3)
    assert len(out) == 3
