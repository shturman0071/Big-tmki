"""Сводный dashboard мониторинга re-index."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_reindex_dashboard(
    *,
    state_path: Path,
    heartbeat_path: Path,
    lock_path: Path,
    progress_log_path: Path | None = None,
) -> dict[str, Any]:
    artifacts_dir = state_path.parent
    log_path = progress_log_path or (artifacts_dir / "reindex-progress-log.jsonl")

    from tmki_ingest.reindex_ops import build_ops_status
    from tmki_ingest.reindex_progress_log import analyze_progress_log, load_progress_log

    ops = build_ops_status(
        state_path=state_path,
        heartbeat_path=heartbeat_path,
        lock_path=lock_path,
        artifacts_dir=artifacts_dir,
    )

    log_entries = load_progress_log(log_path)
    log_analysis = analyze_progress_log(log_entries) if log_entries else None

    report = ops["report"]
    eta_state = report.get("eta_hours")
    eta_log = (log_analysis or {}).get("eta_hours_from_log")

    return {
        "ops": ops,
        "progress_log": {
            "path": str(log_path) if log_path.is_file() else None,
            "analysis": log_analysis,
        },
        "eta": {
            "from_state_hours": eta_state,
            "from_log_hours": eta_log,
        },
        "artifacts": {
            "audit": ops.get("audit_path"),
            "finalize_summary": ops.get("finalize_summary"),
            "progress_log": str(log_path) if log_path.is_file() else None,
        },
    }
