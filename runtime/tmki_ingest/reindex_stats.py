"""Детальная статистика ingest re-index."""

from __future__ import annotations

from typing import Any


def build_ingest_stats(state: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    stats = state.get("stats", {})
    imported = int(stats.get("imported", 0))
    live = int(report.get("live_progress") or 0)
    total = int(report.get("total") or 0)
    checkpoint = int(report.get("processed") or 0)

    return {
        "imported": imported,
        "skip_temp": int(stats.get("skip_temp", 0)),
        "too_large": int(stats.get("too_large", 0)),
        "ocr_failed": int(stats.get("ocr_failed", 0)),
        "errors": int(stats.get("errors", 0)),
        "checkpoint_processed": checkpoint,
        "live_scanned": live,
        "total_candidates": total,
        "pending_scan": max(total - live, 0),
        "import_yield_pct": round(100.0 * imported / live, 1) if live > 0 else None,
        "chunks_v2": int(report.get("chunks_v2") or 0),
    }
