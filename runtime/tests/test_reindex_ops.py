import json
from pathlib import Path

from tmki_ingest.reindex_ops import build_ops_status


def test_ops_status_in_progress(tmp_path: Path):
    state = {
        "processed": ["a"] * 5,
        "total_candidates": 10,
        "stats": {"imported": 4, "errors": 1},
        "recent_errors": [{"path": "x", "error": "Err"}],
        "updated_at": "2026-01-01T00:00:00Z",
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    hb = tmp_path / "reindex-heartbeat.json"
    hb.write_text(json.dumps({"file_index": 6}), encoding="utf-8")

    status = build_ops_status(state_path=state_path, heartbeat_path=hb, lock_path=tmp_path / "nolock")
    assert status["ready_for_finalize"] is False
    assert status["finalize_done"] is False
    assert status["report"]["live_progress"] == 6


def test_ops_status_ready(tmp_path: Path):
    state = {
        "processed": ["a"] * 10,
        "total_candidates": 10,
        "stats": {"imported": 10, "errors": 0},
        "updated_at": "2026-01-01T00:00:00Z",
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    hb = tmp_path / "reindex-heartbeat.json"
    hb.write_text(json.dumps({"file_index": 10}), encoding="utf-8")

    status = build_ops_status(state_path=state_path, heartbeat_path=hb, lock_path=tmp_path / "nolock")
    assert status["ready_for_finalize"] is True
