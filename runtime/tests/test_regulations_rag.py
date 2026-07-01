from pathlib import Path

import pytest

from tmki_policy import build_policy_context, load_org_snapshot
from tmki_rag import load_regulations_chunks, rag_search
from datetime import date

ROOT = Path(__file__).resolve().parents[2]
CHUNKS = Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "chunks.json"


@pytest.mark.skipif(not CHUNKS.is_file(), reason="local regulations import artifacts required")
def test_regulations_chunks_rag_search():
    chunks = load_regulations_chunks(CHUNKS)
    assert len(chunks) >= 1000

    snapshot = load_org_snapshot(ROOT / "schemas/org/examples/satimol-snapshot.example.json")
    ctx = build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )

    resp = rag_search(
        {
            "trace_id": "t-reg",
            "query": "документ TMKI stub",
            "policy_context": ctx,
            "top_k": 5,
        },
        chunks,
    )
    assert resp["stats"]["candidates_before_rls"] == len(chunks)
    assert len(resp["results"]) >= 1
