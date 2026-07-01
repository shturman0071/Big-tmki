"""Tests for wait_reindex_complete.py --once mode."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]


def test_wait_reindex_once_incomplete(tmp_path: Path):
    state = {
        "processed": ["a"],
        "total_candidates": 10,
        "stats": {"imported": 1, "errors": 0},
        "updated_at": "2026-01-01T00:00:00Z",
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    hb = tmp_path / "reindex-heartbeat.json"
    hb.write_text(json.dumps({"file_index": 2}), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/wait_reindex_complete.py",
            "--state",
            str(state_path),
            "--heartbeat",
            str(hb),
            "--once",
        ],
        cwd=RUNTIME,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**dict(__import__("os").environ), "PYTHONPATH": "."},
    )
    assert proc.returncode == 2


def test_wait_reindex_once_complete(tmp_path: Path):
    state = {
        "processed": ["a"] * 5,
        "total_candidates": 5,
        "stats": {"imported": 5, "errors": 0},
        "updated_at": "2026-01-01T00:00:00Z",
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    hb = tmp_path / "reindex-heartbeat.json"
    hb.write_text(json.dumps({"file_index": 5}), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/wait_reindex_complete.py",
            "--state",
            str(state_path),
            "--heartbeat",
            str(hb),
            "--once",
        ],
        cwd=RUNTIME,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**dict(__import__("os").environ), "PYTHONPATH": "."},
    )
    assert proc.returncode == 0
