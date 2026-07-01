"""Сборка ops bundle для handoff и export."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_ops_bundle(
    *,
    artifacts_dir: Path,
    state_path: Path,
    heartbeat_path: Path,
    lock_path: Path,
) -> dict[str, Any]:
    from tmki_ingest.quality_trend import load_partial_quality_files, summarize_quality_trend
    from tmki_ingest.reindex_dashboard import build_reindex_dashboard

    dash = build_reindex_dashboard(
        state_path=state_path,
        heartbeat_path=heartbeat_path,
        lock_path=lock_path,
        progress_log_path=artifacts_dir / "reindex-progress-log.jsonl",
    )

    def _read(name: str) -> dict[str, Any] | None:
        p = artifacts_dir / name
        if not p.is_file():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    partial = load_partial_quality_files(artifacts_dir)
    return {
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dashboard": dash,
        "audit": _read("reindex-audit-latest.json"),
        "partial_quality_latest": _read("quality-partial-latest.json"),
        "partial_quality_trend": summarize_quality_trend(partial),
        "dashboard_saved": _read("reindex-dashboard-latest.json"),
        "paths": {
            "artifacts_dir": str(artifacts_dir),
            "progress_log": str(artifacts_dir / "reindex-progress-log.jsonl"),
            "finalize_summary": str(artifacts_dir / "finalize-summary-latest.json"),
            "ops_bundle": str(artifacts_dir / "reindex-ops-bundle-latest.json"),
        },
    }
