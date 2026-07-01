#!/usr/bin/env python3
"""Экспорт ops bundle: dashboard + audit + quality + trend (read-only)."""

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


def build_ops_bundle(
    *,
    artifacts_dir: Path,
    state_path: Path,
    heartbeat_path: Path,
    lock_path: Path,
) -> dict:
    from tmki_ingest.quality_trend import load_partial_quality_files, summarize_quality_trend
    from tmki_ingest.reindex_dashboard import build_reindex_dashboard

    dash = build_reindex_dashboard(
        state_path=state_path,
        heartbeat_path=heartbeat_path,
        lock_path=lock_path,
        progress_log_path=artifacts_dir / "reindex-progress-log.jsonl",
    )

    def _read(name: str) -> dict | None:
        p = artifacts_dir / name
        if not p.is_file():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    partial = load_partial_quality_files(artifacts_dir)
    return {
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dashboard": dash,
        "audit": _read("reindex-audit-latest.json"),
        "partial_quality_latest": _read("quality-partial-latest.json"),
        "partial_quality_trend": summarize_quality_trend(partial),
        "dashboard_saved": _read("reindex-dashboard-latest.json"),
        "paths": {
            "artifacts_dir": str(artifacts_dir),
            "progress_log": str(artifacts_dir / "reindex-progress-log.jsonl"),
            "finalize_summary": str(artifacts_dir / "finalize-summary-latest.json"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export re-index ops bundle JSON")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--save", nargs="?", const=DEFAULT_STATE.parent / "reindex-ops-bundle-latest.json", type=Path)
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    bundle = build_ops_bundle(
        artifacts_dir=args.state.parent,
        state_path=args.state,
        heartbeat_path=args.heartbeat,
        lock_path=args.lock,
    )

    out_path = args.save
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.stdout:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
    elif out_path is not None:
        print(f"ops bundle saved: {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
