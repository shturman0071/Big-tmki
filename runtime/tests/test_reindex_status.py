import json
import subprocess
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]


def test_reindex_status_script(tmp_path):
    state = {
        "archive_root": "/archive",
        "updated_at": "2026-01-01T00:00:00Z",
        "processed": ["a.txt", "b.txt"],
        "stats": {"imported": 2, "errors": 0, "skip_temp": 1, "ocr_failed": 0},
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "scripts/reindex_status.py", "--state", str(state_path), "--total", "10"],
        cwd=RUNTIME,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**dict(__import__("os").environ), "PYTHONPATH": ".", "PYTHONIOENCODING": "utf-8"},
    )
    assert proc.returncode == 0
    assert "processed: 2/10" in proc.stdout
    assert "imported: 2" in proc.stdout


def test_reindex_status_shows_heartbeat(tmp_path):
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
            "scripts/reindex_status.py",
            "--state",
            str(state_path),
            "--heartbeat",
            str(heartbeat),
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
