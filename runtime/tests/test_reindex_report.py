import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]


def test_reindex_report_script(tmp_path):
    state = {
        "archive_root": "/archive",
        "updated_at": "2026-07-01T10:00:00Z",
        "started_at": "2026-07-01T08:00:00Z",
        "total_candidates": 100,
        "processed": [f"f{i}.txt" for i in range(30)],
        "stats": {"imported": 28, "errors": 2, "skip_temp": 0, "ocr_failed": 0},
        "recent_errors": [{"path": "bad.pdf", "error": "timeout"}],
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    chunks = tmp_path / "chunks-v2.json"
    chunks.write_text(json.dumps({"chunks": [{"chunk_id": "c1"}] * 28}), encoding="utf-8")
    missing = tmp_path / "missing.json"

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/reindex_report.py",
            "--state",
            str(state_path),
            "--heartbeat",
            str(missing),
            "--lock",
            str(missing),
            "--json",
        ],
        cwd=RUNTIME,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**dict(__import__("os").environ), "PYTHONPATH": ".", "PYTHONIOENCODING": "utf-8"},
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["processed"] == 30
    assert data["live_progress"] == 30
    assert data["percent"] == 30.0
    assert data["complete"] is False
    assert data["eta_hours"] is not None


def test_reindex_report_shows_heartbeat(tmp_path):
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(
        json.dumps({"processed": ["a.txt"], "stats": {"imported": 1, "errors": 0}, "total_candidates": 5}),
        encoding="utf-8",
    )
    heartbeat = tmp_path / "reindex-heartbeat.json"
    heartbeat.write_text(
        json.dumps(
            {
                "current_file": "big/archive.pdf",
                "file_index": 3,
                "total_candidates": 5,
                "updated_at": "2026-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/reindex_report.py",
            "--state",
            str(state_path),
            "--heartbeat",
            str(heartbeat),
            "--lock",
            str(tmp_path / "nolock"),
        ],
        cwd=RUNTIME,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**dict(__import__("os").environ), "PYTHONPATH": ".", "PYTHONIOENCODING": "utf-8"},
    )
    assert proc.returncode == 0
    assert "current:" in proc.stdout
    assert "archive.pdf" in proc.stdout


def test_estimate_eta_hours():
    from scripts.reindex_report import estimate_eta_hours

    started = datetime(2026, 7, 1, 8, 0, 0, tzinfo=timezone.utc)
    now = datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc)
    eta = estimate_eta_hours(started=started, live_progress=3000, total=10000, now=now)
    assert eta is not None
    assert 4.5 < eta < 5.5
