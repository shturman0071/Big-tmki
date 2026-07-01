import json
from pathlib import Path
from unittest.mock import MagicMock

from tmki_ingest.quality_snapshot_schedule import (
    pending_quality_threshold,
    try_scheduled_partial_snapshot,
)


def test_pending_quality_threshold_skips_existing(tmp_path: Path):
    (tmp_path / "quality-partial-p75.json").write_text("{}", encoding="utf-8")
    assert pending_quality_threshold(81.0, tmp_path) == 80
    assert pending_quality_threshold(74.0, tmp_path) is None


def test_try_scheduled_partial_snapshot_writes_at_threshold(tmp_path: Path):
    state = {
        "processed": ["a"] * 850,
        "total_candidates": 1000,
        "stats": {"imported": 800, "errors": 0, "skip_temp": 0, "too_large": 0},
        "updated_at": "2026-01-01T00:00:00Z",
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    hb = tmp_path / "reindex-heartbeat.json"
    hb.write_text(json.dumps({"file_index": 850}), encoding="utf-8")
    for t in (75, 80):
        (tmp_path / f"quality-partial-p{t}.json").write_text("{}", encoding="utf-8")

    benchmark = MagicMock(return_value={"v2_count": 100, "hybrid": True, "rows": []})
    saved = try_scheduled_partial_snapshot(
        state_path=state_path,
        heartbeat_path=hb,
        lock_path=tmp_path / "nolock",
        run_benchmark=benchmark,
    )
    assert saved == 85
    assert (tmp_path / "quality-partial-p85.json").is_file()
    assert benchmark.called
