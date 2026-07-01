import json
from pathlib import Path

from tmki_ingest.preflight_finalize import build_preflight_finalize
from tmki_ingest.reindex_complete import build_reindex_complete_snapshot


def _write_state(tmp_path: Path, *, processed: int, total: int, imported: int) -> tuple[Path, Path]:
    state = {
        "processed": ["a"] * processed,
        "total_candidates": total,
        "stats": {
            "imported": imported,
            "duplicate": 0,
            "rejected": 0,
            "ocr_failed": 0,
            "too_large": 0,
            "skip_temp": 0,
            "errors": 0,
        },
        "updated_at": "2026-01-01T00:00:00Z",
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    hb = tmp_path / "reindex-heartbeat.json"
    hb.write_text(json.dumps({"file_index": processed}), encoding="utf-8")
    (tmp_path / "chunks-v2.json").write_text(json.dumps({"chunks": [{"id": "c1"}]}), encoding="utf-8")
    return state_path, hb


def test_build_preflight_finalize_complete(tmp_path: Path):
    state_path, hb = _write_state(tmp_path, processed=10, total=10, imported=9)
    out = build_preflight_finalize(
        state_path=state_path,
        heartbeat_path=hb,
        lock_path=tmp_path / "nolock",
        dsn="",
    )
    assert out["ready"] is True
    assert out["report"]["complete"] is True


def test_build_reindex_complete_snapshot(tmp_path: Path):
    state_path, hb = _write_state(tmp_path, processed=10, total=10, imported=9)
    snap = build_reindex_complete_snapshot(
        artifacts_dir=tmp_path,
        state_path=state_path,
        heartbeat_path=hb,
        lock_path=tmp_path / "nolock",
        dsn="",
    )
    assert snap["kind"] == "reindex_complete"
    assert snap["preflight"]["ready"] is True
    assert "TMKI re-index handoff" in snap["handoff_text"]
    assert snap["ops_bundle"]["dashboard"]["ops"]["report"]["live_progress"] == 10
