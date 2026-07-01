"""Текстовая сводка handoff по ops bundle."""

from __future__ import annotations

from typing import Any


def format_handoff(bundle: dict[str, Any]) -> str:
    lines = ["TMKI re-index handoff", ""]
    dash = bundle.get("dashboard") or {}
    ops = dash.get("ops") or {}
    r = ops.get("report") or {}
    ing = ops.get("ingest_stats") or {}
    err = (ops.get("errors") or {}).get("errors_total", 0)

    if r:
        lines.append(f"Progress: {r.get('live_progress')}/{r.get('total')} ({r.get('percent')}%)")
        if r.get("complete"):
            lines.append("Status: complete")
        lines.append(f"Imported: {ing.get('imported')}  chunks_v2: {ing.get('chunks_v2')}  errors: {err}")
        if ing.get("import_yield_pct") is not None:
            lines.append(
                f"Yield: {ing['import_yield_pct']}%  skip_temp: {ing.get('skip_temp')}  too_large: {ing.get('too_large')}"
            )

    eta = dash.get("eta") or {}
    if eta.get("from_state_hours") is not None:
        lines.append(f"ETA (state): ~{eta['from_state_hours']} h")
    if eta.get("from_log_hours") is not None:
        lines.append(f"ETA (log): ~{eta['from_log_hours']} h")

    if ops.get("ready_for_finalize"):
        lines.append("Ready for finalize: yes")
    elif ops.get("finalize_done"):
        lines.append("Finalize: done")

    trend = bundle.get("partial_quality_trend") or {}
    points = trend.get("points") or []
    if points:
        lines.append("")
        lines.append("Partial quality trend:")
        for p in points:
            lines.append(f"  {p.get('percent', 0):.1f}%  v2={p.get('v2_count')}  avg={p.get('avg_score')}")

    paths = bundle.get("paths") or {}
    if paths.get("ops_bundle"):
        lines.append("")
        lines.append(f"Bundle: {paths['ops_bundle']}")

    return "\n".join(lines)
