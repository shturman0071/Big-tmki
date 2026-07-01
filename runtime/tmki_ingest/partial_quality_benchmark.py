"""Hybrid v2 quality benchmark для partial snapshots."""

from __future__ import annotations

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUERIES = ["промбезопасность", "кран", "маркшейдерская", "ОПО", "договор"]


def run_v2_hybrid_benchmark(top_k: int = 3) -> dict:
    from tmki_policy import build_policy_context, load_org_snapshot
    from tmki_rag import VectorChunkIndex, hybrid_score_fn, rag_search_with_index
    from tmki_rag.chunks_io import DEFAULT_REGULATIONS_CHUNKS_V2, load_chunks_file
    from tmki_rag.search import _default_score

    if not DEFAULT_REGULATIONS_CHUNKS_V2.is_file():
        raise FileNotFoundError(f"chunks-v2 не найден: {DEFAULT_REGULATIONS_CHUNKS_V2}")

    v2 = load_chunks_file(DEFAULT_REGULATIONS_CHUNKS_V2)
    snapshot = load_org_snapshot(ROOT / "schemas/org/examples/satimol-snapshot.example.json")
    ctx = build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )
    index = VectorChunkIndex()
    index.add(v2)
    score_fn = hybrid_score_fn(index, _default_score)

    rows = []
    for q in QUERIES:
        resp = rag_search_with_index(
            {"trace_id": "partial", "query": q, "policy_context": ctx, "top_k": top_k},
            index,
            score_fn=score_fn,
        )
        n = len(resp["results"])
        avg = sum(r["score"] for r in resp["results"]) / n if n else 0.0
        rows.append({"query": q, "hits": n, "avg_score": avg})

    return {"v2_count": len(v2), "hybrid": True, "rows": rows}
