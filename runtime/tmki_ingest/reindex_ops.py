"""Единый ops-статус re-index для мониторинга и finalize."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_ops_status(
    *,
    state_path: Path,
    heartbeat_path: Path,
    lock_path: Path,
    artifacts_dir: Path | None = None,
) -> dict[str, Any]:
    artifacts_dir = artifacts_dir or state_path.parent
    state = json.loads(state_path.read_text(encoding="utf-8"))

    from tmki_ingest.reindex_errors_lib import load_error_audit
    from tmki_ingest.reindex_progress import build_reindex_report

    report = build_reindex_report(
        state_path=state_path,
        heartbeat_path=heartbeat_path,
        lock_path=lock_path,
    )
    errors = load_error_audit(state, limit=5)
    finalize_marker = artifacts_dir / "finalize-done.json"
    summary_path = artifacts_dir / "finalize-summary-latest.json"

    ready_for_finalize = bool(report.get("complete")) and report.get("lock_pid") is None

    return {
        "report": report,
        "errors": errors,
        "ready_for_finalize": ready_for_finalize,
        "finalize_done": finalize_marker.is_file(),
        "finalize_summary": str(summary_path) if summary_path.is_file() else None,
        "audit_path": str(artifacts_dir / "reindex-audit-latest.json")
        if (artifacts_dir / "reindex-audit-latest.json").is_file()
        else None,
    }
