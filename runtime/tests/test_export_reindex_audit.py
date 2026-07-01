import json
import subprocess
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]


def test_export_reindex_audit(tmp_path: Path):
    state = {
        "processed": ["a"] * 3,
        "total_candidates": 10,
        "stats": {"imported": 2, "errors": 1, "skip_temp": 0},
        "recent_errors": [{"path": "bad.pdf", "error": "TimeoutError"}],
        "updated_at": "2026-01-01T00:00:00Z",
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    hb = tmp_path / "reindex-heartbeat.json"
    hb.write_text(json.dumps({"file_index": 3}), encoding="utf-8")
    out = tmp_path / "audit.json"

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/export_reindex_audit.py",
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
    assert data["report"]["live_progress"] == 3
    assert data["errors"]["errors_total"] == 1
