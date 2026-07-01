"""Метаданные partial quality snapshot во время re-index."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def augment_quality_payload(payload: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "snapshot_kind": "partial_reindex",
        "reindex_percent": report.get("percent"),
        "reindex_progress": report.get("live_progress"),
        "reindex_total": report.get("total"),
        "chunks_v2": report.get("chunks_v2"),
        "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def write_partial_quality_snapshot(
    *,
    save_path: Path,
    report: dict[str, Any],
    payload: dict[str, Any],
) -> Path:
    save_path.parent.mkdir(parents=True, exist_ok=True)
    out = augment_quality_payload(payload, report)
    save_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return save_path
