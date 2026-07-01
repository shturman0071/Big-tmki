import json
import subprocess
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]


def test_reindex_errors_summary(tmp_path):
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(
        json.dumps(
            {
                "stats": {"errors": 3},
                "recent_errors": [
                    {"path": "a.pdf", "error": "KeyError: 'skip_temp'"},
                    {"path": "b.pdf", "error": "KeyError: 'skip_temp'"},
                    {"path": "c.pdf", "error": "TimeoutError: read"},
                ],
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, "scripts/reindex_errors.py", "--state", str(state_path), "--summary"],
        cwd=RUNTIME,
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "PYTHONPATH": "."},
    )
    assert proc.returncode == 0
    assert "KeyError" in proc.stdout
    assert "TimeoutError" in proc.stdout
