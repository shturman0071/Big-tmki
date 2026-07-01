import json
from pathlib import Path

from tmki_ingest.reindex_dashboard import build_reindex_dashboard


def test_build_reindex_dashboard(tmp_path: Path):
    state = {
        "processed": ["a"] * 5,
        "total_candidates": 10,
        "stats": {"imported": 4, "errors": 0, "skip_temp": 1, "too_large": 0},
        "updated_at": "2026-01-01T00:00:00Z",
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    hb = tmp_path / "reindex-heartbeat.json"
    hb.write_text(json.dumps({"file_index": 6}), encoding="utf-8")

    dash = build_reindex_dashboard(
        state_path=state_path,
        heartbeat_path=hb,
        lock_path=tmp_path / "nolock",
    )
    assert dash["ops"]["report"]["live_progress"] == 6
    assert "eta" in dash
