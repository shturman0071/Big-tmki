from datetime import date
from pathlib import Path

from tmki_policy import build_policy_context, load_org_snapshot
from tmki_runtime import run_mvp
from tmki_runtime.mvp import load_chunks

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "schemas/org/examples/satimol-snapshot.example.json"
CHUNKS = ROOT / "schemas/document/examples/satimol-chunks.example.json"


def test_mvp_satimol_chefmarkscheider():
    snapshot = load_org_snapshot(SNAPSHOT)
    ctx = build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )
    result = run_mvp(
        message="маркшейдерская съёмка на участке КС",
        policy_context=ctx,
        chunks=load_chunks(CHUNKS),
        trace_id="00000000-0000-4000-8000-000000000001",
        run_id="00000000-0000-4000-8000-000000000002",
    )

    assert result["loop_state"]["loop_state"] == "loop_complete"
    assert result["output"]["confidence"] == "high"
    assert len(result["output"]["citations"]) >= 1
    event_types = [e["event_type"] for e in result["audit_events"]]
    assert "run_started" in event_types
    assert "document_accessed" in event_types
    assert "judge_pass" in event_types
    assert "run_completed" in event_types
