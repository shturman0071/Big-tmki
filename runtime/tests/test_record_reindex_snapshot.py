import json
import subprocess
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]


def test_record_reindex_snapshot(tmp_path: Path):
    state = {
        "processed": ["a"] * 4,
        "total_candidates": 10,
        "stats": {"imported": 3, "errors": 0, "skip_temp": 1, "too_large": 0},
        "updated_at": "2026-01-01T00:00:00Z",
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    hb = tmp_path / "reindex-heartbeat.json"
    hb.write_text(json.dumps({"file_index": 5}), encoding="utf-8")
    log_path = tmp_path / "progress.jsonl"

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/record_reindex_snapshot.py",
            "--state",
            str(state_path),
            "--heartbeat",
            str(hb),
            "--lock",
            str(tmp_path / "nolock"),
            "--log",
            str(log_path),
        ],
        cwd=RUNTIME,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**dict(__import__("os").environ), "PYTHONPATH": "."},
    )
    assert proc.returncode == 0
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["live_progress"] == 5
    assert row["ingest"]["imported"] == 3
