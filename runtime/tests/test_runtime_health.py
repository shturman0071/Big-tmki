import subprocess
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]


def test_check_runtime_health_ok():
    proc = subprocess.run(
        [sys.executable, "scripts/check_runtime_health.py"],
        cwd=RUNTIME,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={
            **dict(__import__("os").environ),
            "PYTHONPATH": ".",
            "TMKI_OCR_MODE": "stub",
            "DATABASE_URL": "",
        },
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "[ok] python packages" in proc.stdout
