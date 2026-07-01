"""Preflight-проверки перед finalize_regulations_index."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def build_preflight_finalize(
    *,
    state_path: Path,
    heartbeat_path: Path,
    lock_path: Path,
    dsn: str | None = None,
) -> dict[str, Any]:
    from tmki_ingest.quality_trend import load_partial_quality_files, summarize_quality_trend
    from tmki_ingest.reindex_progress import build_reindex_report

    report = build_reindex_report(
        state_path=state_path,
        heartbeat_path=heartbeat_path,
        lock_path=lock_path,
    )

    checks: list[dict[str, object]] = []
    ok = True

    def add(name: str, passed: bool, detail: str, *, blocking: bool = True) -> None:
        nonlocal ok
        checks.append({"name": name, "ok": passed, "detail": detail, "blocking": blocking})
        if blocking and not passed:
            ok = False

    add("reindex_complete", report["complete"], f"{report['live_progress']}/{report['total']}")
    add("chunks_v2", report["chunks_v2"] > 0, f"{report['chunks_v2']} records")
    add("reindex_running", report["lock_pid"] is None, f"lock_pid={report['lock_pid']}", blocking=False)

    db_url = dsn if dsn is not None else os.environ.get("DATABASE_URL", "")
    if db_url:
        try:
            import psycopg

            with psycopg.connect(db_url, connect_timeout=5) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            add("database_url", True, "connected")
        except Exception as exc:
            add("database_url", False, str(exc))
    else:
        add("database_url", False, "DATABASE_URL not set (finalize needs Docker/pgvector)", blocking=False)

    trend = summarize_quality_trend(load_partial_quality_files(state_path.parent))
    add(
        "partial_quality_snapshots",
        trend.get("count", 0) > 0,
        f"{trend.get('count', 0)} snapshots",
        blocking=False,
    )

    ops_bundle = state_path.parent / "reindex-ops-bundle-latest.json"
    add("ops_bundle", ops_bundle.is_file(), str(ops_bundle), blocking=False)

    error_audit = None
    if report.get("errors", 0):
        state = json.loads(state_path.read_text(encoding="utf-8"))
        from tmki_ingest.reindex_errors_lib import load_error_audit

        error_audit = load_error_audit(state, limit=10)
        add(
            "reindex_errors",
            True,
            f"{report['errors']} errors (review reindex_errors.py)",
            blocking=False,
        )

    out: dict[str, Any] = {"ready": ok, "checks": checks, "report": report}
    if error_audit is not None:
        out["error_audit"] = error_audit
    return out
