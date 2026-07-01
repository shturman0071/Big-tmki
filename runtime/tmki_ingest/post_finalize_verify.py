"""Проверки после finalize_regulations_index."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_post_finalize_verify(artifacts_dir: Path, *, dsn: str | None = None) -> dict[str, Any]:
    from tmki_ingest.finalize_report import build_post_finalize_report, pgvector_row_count

    report = build_post_finalize_report(artifacts_dir, dsn=dsn)
    checks: list[dict[str, object]] = []
    ok = True

    def add(name: str, passed: bool, detail: str, *, blocking: bool = True) -> None:
        nonlocal ok
        checks.append({"name": name, "ok": passed, "detail": detail, "blocking": blocking})
        if blocking and not passed:
            ok = False

    def _exists(name: str) -> bool:
        return (artifacts_dir / name).is_file()

    add("finalize_done", _exists("finalize-done.json"), "finalize-done.json")
    add("finalize_summary", _exists("finalize-summary-latest.json"), "finalize-summary-latest.json")
    add("finalize_handoff", _exists("finalize-handoff.txt"), "finalize-handoff.txt")
    add("finalize_ops_bundle", _exists("finalize-ops-bundle-latest.json"), "finalize-ops-bundle-latest.json")
    add("quality_benchmark", _exists("quality-benchmark-final.json"), "quality-benchmark-final.json")

    qb = report.get("quality_benchmark") or {}
    add("quality_v2", bool(qb.get("v2_count")), f"v2_count={qb.get('v2_count')}")

    pg_rows = report.get("pgvector_rows")
    if pg_rows is not None:
        add("pgvector_rows", pg_rows > 0, f"{pg_rows} rows")
    else:
        add("pgvector_rows", False, "DATABASE_URL not set or DB unreachable", blocking=False)

    reindex = report.get("reindex") or {}
    chunks_v2 = reindex.get("chunks_v2")
    if pg_rows is not None and chunks_v2:
        add(
            "pgvector_vs_chunks",
            pg_rows >= int(chunks_v2),
            f"pgvector={pg_rows} chunks_v2={chunks_v2}",
            blocking=False,
        )

    complete_path = artifacts_dir / "reindex-complete-latest.json"
    if complete_path.is_file():
        complete = json.loads(complete_path.read_text(encoding="utf-8"))
        add("reindex_complete_snapshot", True, str(complete_path), blocking=False)
        add(
            "preflight_was_ready",
            bool((complete.get("preflight") or {}).get("ready")),
            "from reindex-complete snapshot",
            blocking=False,
        )

    return {"verified": ok, "checks": checks, "report": report}
