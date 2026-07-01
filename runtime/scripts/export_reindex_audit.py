#!/usr/bin/env python3
"""Экспорт аудита re-index: прогресс + ошибки + stats (read-only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_STATE = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "reindex-state.json"
)
DEFAULT_HEARTBEAT = DEFAULT_STATE.parent / "reindex-heartbeat.json"
DEFAULT_LOCK = DEFAULT_STATE.parent / "reindex.lock"


def build_audit(
    *,
    state_path: Path,
    heartbeat_path: Path,
    lock_path: Path,
    error_limit: int = 50,
) -> dict:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    from tmki_ingest.reindex_errors_lib import load_error_audit
    from tmki_ingest.reindex_progress import build_reindex_report

    report = build_reindex_report(
        state_path=state_path,
        heartbeat_path=heartbeat_path,
        lock_path=lock_path,
    )
    from tmki_ingest.reindex_stats import build_ingest_stats

    return {
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "report": report,
        "errors": load_error_audit(state, limit=error_limit),
        "stats": state.get("stats", {}),
        "ingest_stats": build_ingest_stats(state, report),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export re-index audit JSON")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--save", type=Path, default=None, help="Путь к JSON (default: artifacts/.../reindex-audit-latest.json)")
    parser.add_argument("--stdout", action="store_true", help="Печатать JSON в stdout")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    audit = build_audit(
        state_path=args.state,
        heartbeat_path=args.heartbeat,
        lock_path=args.lock,
    )

    out_path = args.save or (args.state.parent / "reindex-audit-latest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.stdout:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
    else:
        print(f"audit saved: {out_path}", file=sys.stderr)
        print(
            f"progress: {audit['report']['live_progress']}/{audit['report']['total']} "
            f"errors={audit['errors']['errors_total']}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
