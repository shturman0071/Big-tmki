import json
from datetime import datetime, timezone
from pathlib import Path

from tmki_ingest.reindex_progress_log import analyze_progress_log, estimate_eta_hours_from_log, load_progress_log


def test_estimate_eta_from_log(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    rows = [
        {
            "recorded_at": "2026-07-01T10:00:00Z",
            "live_progress": 1000,
            "ingest": {"total_candidates": 10000},
        },
        {
            "recorded_at": "2026-07-01T11:00:00Z",
            "live_progress": 2000,
            "ingest": {"total_candidates": 10000},
        },
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    entries = load_progress_log(log)
    now = datetime(2026, 7, 1, 11, 0, 0, tzinfo=timezone.utc)
    eta = estimate_eta_hours_from_log(entries, now=now)
    assert eta is not None
    assert 7.9 <= eta <= 8.1


def test_analyze_progress_log_empty():
    assert analyze_progress_log([])["points"] == 0
