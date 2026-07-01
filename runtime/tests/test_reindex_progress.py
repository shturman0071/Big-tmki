from pathlib import Path

from tmki_ingest.reindex_progress import build_reindex_report, estimate_eta_hours


def test_estimate_eta_hours_none_at_start():
    assert estimate_eta_hours(started=None, live_progress=0, total=100) is None


def test_estimate_eta_hours_zero_when_complete():
    from datetime import datetime, timezone

    started = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert estimate_eta_hours(started=started, live_progress=100, total=100) == 0.0


def test_build_reindex_report_complete(tmp_path: Path):
    state = {
        "processed": ["a"] * 10,
        "total_candidates": 10,
        "stats": {"imported": 8, "errors": 1, "skip_temp": 0, "ocr_failed": 0},
        "updated_at": "2026-01-01T00:00:00Z",
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(__import__("json").dumps(state), encoding="utf-8")
    hb = tmp_path / "reindex-heartbeat.json"
    hb.write_text(__import__("json").dumps({"file_index": 10}), encoding="utf-8")

    report = build_reindex_report(state_path=state_path, heartbeat_path=hb, lock_path=None)
    assert report["complete"] is True
    assert report["live_progress"] == 10


def test_build_reindex_report_in_progress(tmp_path: Path):
    state = {
        "processed": ["a"] * 3,
        "total_candidates": 10,
        "stats": {"imported": 2, "errors": 0},
        "updated_at": "2026-01-01T00:00:00Z",
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(__import__("json").dumps(state), encoding="utf-8")
    hb = tmp_path / "reindex-heartbeat.json"
    hb.write_text(__import__("json").dumps({"file_index": 5}), encoding="utf-8")

    report = build_reindex_report(state_path=state_path, heartbeat_path=hb, lock_path=None)
    assert report["complete"] is False
    assert report["live_progress"] == 5
