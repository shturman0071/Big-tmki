"""Тренд partial quality snapshots во время re-index."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_partial_quality_files(artifacts_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(artifacts_dir.glob("quality-partial-p*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        rows.append({**data, "_path": str(path)})
    rows.sort(key=lambda r: float(r.get("reindex_percent") or 0))
    return rows


def summarize_quality_trend(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    points = []
    for snap in snapshots:
        pct = snap.get("reindex_percent")
        rows = snap.get("rows") or []
        avg = None
        if rows:
            scores = [float(r.get("avg_score") or 0) for r in rows if r.get("hits")]
            avg = round(sum(scores) / len(scores), 4) if scores else 0.0
        points.append(
            {
                "percent": pct,
                "v2_count": snap.get("v2_count"),
                "avg_score": avg,
                "path": snap.get("_path"),
            }
        )
    return {"points": points, "count": len(points)}
