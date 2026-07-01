#!/usr/bin/env python3
"""Печать handoff-сводки re-index (read-only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_STATE = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "reindex-state.json"
)
DEFAULT_HEARTBEAT = DEFAULT_STATE.parent / "reindex-heartbeat.json"
DEFAULT_LOCK = DEFAULT_STATE.parent / "reindex.lock"
DEFAULT_BUNDLE = DEFAULT_STATE.parent / "reindex-ops-bundle-latest.json"
DEFAULT_ARTIFACTS = DEFAULT_STATE.parent
DEFAULT_FINALIZE_SUMMARY = DEFAULT_ARTIFACTS / "finalize-summary-latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Print re-index handoff summary")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--bundle", type=Path, default=None, help="Готовый ops bundle JSON")
    parser.add_argument("--finalize", action="store_true", help="Post-finalize handoff из summary")
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--save", type=Path, default=None, help="Сохранить текст handoff")
    args = parser.parse_args()

    if args.finalize:
        from tmki_ingest.finalize_report import build_post_finalize_report
        from tmki_ingest.handoff_summary import format_finalize_handoff

        if args.bundle and args.bundle.is_file():
            report = json.loads(args.bundle.read_text(encoding="utf-8"))
        elif DEFAULT_FINALIZE_SUMMARY.is_file():
            report = json.loads(DEFAULT_FINALIZE_SUMMARY.read_text(encoding="utf-8"))
        else:
            report = build_post_finalize_report(args.artifacts)
        text = format_finalize_handoff(report)
    else:
        from tmki_ingest.handoff_summary import format_handoff
        from tmki_ingest.ops_bundle import build_ops_bundle

        if args.bundle and args.bundle.is_file():
            bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        elif args.state.is_file():
            bundle = build_ops_bundle(
                artifacts_dir=args.state.parent,
                state_path=args.state,
                heartbeat_path=args.heartbeat,
                lock_path=args.lock,
            )
        else:
            print("state или bundle не найден", file=sys.stderr)
            return 1
        text = format_handoff(bundle)

    print(text)
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_text(text + "\n", encoding="utf-8")
        print(f"\nsaved: {args.save}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
