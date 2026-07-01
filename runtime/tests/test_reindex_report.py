import json
import subprocess
import sys
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

    proc = subprocess.run(
        [sys.executable, "scripts/reindex_report.py", "--state", str(state_path), "--json"],
        cwd=RUNTIME,
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "PYTHONPATH": "."},
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["processed"] == 30
    assert data["percent"] == 30.0
    assert data["eta_hours"] is not None
