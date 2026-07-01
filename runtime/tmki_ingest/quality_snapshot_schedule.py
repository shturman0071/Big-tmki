"""Плановые partial quality snapshots по порогам прогресса."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

QUALITY_SNAPSHOT_THRESHOLDS: tuple[int, ...] = (75, 80, 85, 90, 95)


def pending_quality_threshold(percent: float, artifacts_dir: Path) -> int | None:
    for threshold in QUALITY_SNAPSHOT_THRESHOLDS:
        if percent >= threshold and not (artifacts_dir / f"quality-partial-p{threshold}.json").is_file():
            return threshold
    return None


def try_scheduled_partial_snapshot(
    *,
    state_path: Path,
    heartbeat_path: Path,
    lock_path: Path,
    run_benchmark: Callable[[], dict[str, Any]],
) -> int | None:
    from tmki_ingest.quality_snapshot import write_partial_quality_snapshot
    from tmki_ingest.reindex_progress import build_reindex_report

    report = build_reindex_report(
        state_path=state_path,
        heartbeat_path=heartbeat_path,
        lock_path=lock_path,
    )
    if report.get("complete"):
        return None

    percent = float(report.get("percent") or 0)
    threshold = pending_quality_threshold(percent, state_path.parent)
    if threshold is None:
        return None

    payload = run_benchmark()
    artifacts_dir = state_path.parent
    out = artifacts_dir / f"quality-partial-p{threshold}.json"
    latest = artifacts_dir / "quality-partial-latest.json"
    labeled_report = {**report, "percent": float(threshold)}
    write_partial_quality_snapshot(save_path=out, report=labeled_report, payload=payload)
    write_partial_quality_snapshot(save_path=latest, report=report, payload=payload)
    return threshold
