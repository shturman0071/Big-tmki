import json
from pathlib import Path

from tmki_ingest.pipeline_status import build_pipeline_status


def _write_state(tmp_path: Path, *, processed: int, total: int) -> tuple[Path, Path]:
    state = {
        "processed": ["a"] * processed,
        "total_candidates": total,
        "stats": {"imported": processed, "errors": 0, "skip_temp": 0, "too_large": 0},
        "updated_at": "2026-01-01T00:00:00Z",
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    hb = tmp_path / "reindex-heartbeat.json"
    hb.write_text(json.dumps({"file_index": processed}), encoding="utf-8")
    (tmp_path / "chunks-v2.json").write_text(json.dumps({"chunks": [{"id": "c1"}]}), encoding="utf-8")
    return state_path, hb


def test_pipeline_status_ready_for_finalize(tmp_path: Path):
    state_path, hb = _write_state(tmp_path, processed=10, total=10)
    status = build_pipeline_status(
        artifacts_dir=tmp_path,
        state_path=state_path,
        heartbeat_path=hb,
        lock_path=tmp_path / "nolock",
    )
    assert status["phase"] == "ready_for_finalize"
    assert "finalize" in status["next_step"]


def test_pipeline_status_post_finalize(tmp_path: Path):
    state_path, hb = _write_state(tmp_path, processed=10, total=10)
    (tmp_path / "finalize-done.json").write_text("{}", encoding="utf-8")
    status = build_pipeline_status(
        artifacts_dir=tmp_path,
        state_path=state_path,
        heartbeat_path=hb,
        lock_path=tmp_path / "nolock",
    )
    assert status["phase"] == "post_finalize"
    assert status["next_step"] == "post_finalize_checklist.ps1"
