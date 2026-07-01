"""Сводка после finalize: audit, quality benchmark, pgvector."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def pgvector_row_count(dsn: str | None = None) -> int | None:
    url = dsn or os.environ.get("DATABASE_URL", "")
    if not url:
        return None
    try:
        import psycopg

        with psycopg.connect(url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM tmki_chunks")
                row = cur.fetchone()
                return int(row[0]) if row else 0
    except Exception:
        return None


def build_post_finalize_report(artifacts_dir: Path, *, dsn: str | None = None) -> dict[str, Any]:
    audit = _read_json(artifacts_dir / "reindex-audit-latest.json")
    quality = _read_json(artifacts_dir / "quality-benchmark-final.json")
    partial_quality = _read_json(artifacts_dir / "quality-partial-latest.json")
    finalize_marker = _read_json(artifacts_dir / "finalize-done.json")
    ops_bundle = _read_json(artifacts_dir / "reindex-ops-bundle-latest.json")

    from tmki_ingest.quality_trend import load_partial_quality_files, summarize_quality_trend

    partial_trend = summarize_quality_trend(load_partial_quality_files(artifacts_dir))

    reindex_report = (audit or {}).get("report")
    pg_rows = pgvector_row_count(dsn)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "reindex": reindex_report,
        "errors_total": (audit or {}).get("errors", {}).get("errors_total"),
        "quality_benchmark": quality,
        "partial_quality_latest": partial_quality,
        "partial_quality_trend": partial_trend,
        "ops_bundle": ops_bundle,
        "pgvector_rows": pg_rows,
        "finalize_marker": finalize_marker,
        "artifacts": {
            "audit": str(artifacts_dir / "reindex-audit-latest.json"),
            "quality": str(artifacts_dir / "quality-benchmark-final.json"),
            "summary": str(artifacts_dir / "finalize-summary-latest.json"),
            "ops_bundle": str(artifacts_dir / "reindex-ops-bundle-latest.json"),
            "finalize_ops_bundle": str(artifacts_dir / "finalize-ops-bundle-latest.json"),
        },
    }
