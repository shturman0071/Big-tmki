#!/usr/bin/env python3
"""Проверка готовности к finalize после re-index (read-only)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULT_STATE = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "reindex-state.json"
)
DEFAULT_HEARTBEAT = DEFAULT_STATE.parent / "reindex-heartbeat.json"
DEFAULT_LOCK = DEFAULT_STATE.parent / "reindex.lock"


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight before finalize_regulations_index")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    from tmki_ingest.reindex_progress import build_reindex_report

    report = build_reindex_report(
        state_path=args.state,
        heartbeat_path=args.heartbeat,
        lock_path=args.lock,
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

    dsn = os.environ.get("DATABASE_URL", "")
    if dsn:
        try:
            import psycopg

            with psycopg.connect(dsn, connect_timeout=5) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            add("database_url", True, "connected")
        except Exception as exc:
            add("database_url", False, str(exc))
    else:
        add("database_url", False, "DATABASE_URL not set (finalize needs Docker/pgvector)", blocking=False)

    from tmki_ingest.quality_trend import load_partial_quality_files, summarize_quality_trend

    trend = summarize_quality_trend(load_partial_quality_files(args.state.parent))
    add(
        "partial_quality_snapshots",
        trend.get("count", 0) > 0,
        f"{trend.get('count', 0)} snapshots",
        blocking=False,
    )

    ops_bundle = args.state.parent / "reindex-ops-bundle-latest.json"
    add("ops_bundle", ops_bundle.is_file(), str(ops_bundle), blocking=False)

    error_audit = None
    if report.get("errors", 0):
        state = json.loads(args.state.read_text(encoding="utf-8"))
        from tmki_ingest.reindex_errors_lib import load_error_audit

        error_audit = load_error_audit(state, limit=10)
        add(
            "reindex_errors",
            True,
            f"{report['errors']} errors (review reindex_errors.py)",
            blocking=False,
        )

    out: dict[str, object] = {"ready": ok, "checks": checks, "report": report}
    if error_audit is not None:
        out["error_audit"] = error_audit

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("TMKI preflight finalize\n")
        for row in checks:
            tag = "ok" if row["ok"] else ("warn" if not row["blocking"] else "fail")
            print(f"  [{tag}] {row['name']}: {row['detail']}")
        print(f"\nready: {ok}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
