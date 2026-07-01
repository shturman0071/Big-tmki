import json
import subprocess
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]


def test_export_ops_bundle(tmp_path: Path):
    state = {
        "processed": ["a"] * 3,
        "total_candidates": 10,
        "stats": {"imported": 2, "errors": 0, "skip_temp": 0, "too_large": 0},
        "updated_at": "2026-01-01T00:00:00Z",
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    hb = tmp_path / "reindex-heartbeat.json"
    hb.write_text(json.dumps({"file_index": 4}), encoding="utf-8")
    out = tmp_path / "bundle.json"

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/export_reindex_ops_bundle.py",
            "--state",
            str(state_path),
            "--heartbeat",
            str(hb),
            "--lock",
            str(tmp_path / "nolock"),
            "--save",
            str(out),
        ],
        cwd=RUNTIME,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**dict(__import__("os").environ), "PYTHONPATH": "."},
    )
    assert proc.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "dashboard" in data
    assert data["dashboard"]["ops"]["report"]["live_progress"] == 4
