#!/usr/bin/env python3
"""Сводный отчёт после finalize_regulations_index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_ARTIFACTS = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Post-finalize summary report")
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--save", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from tmki_ingest.finalize_report import build_post_finalize_report

    report = build_post_finalize_report(args.artifacts)
    out_path = args.save or (args.artifacts / "finalize-summary-latest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("TMKI post-finalize report\n")
        if report.get("reindex"):
            r = report["reindex"]
            print(f"  re-index: {r.get('live_progress')}/{r.get('total')} chunks_v2={r.get('chunks_v2')}")
        if report.get("pgvector_rows") is not None:
            print(f"  pgvector rows: {report['pgvector_rows']}")
        if report.get("quality_benchmark"):
            qb = report["quality_benchmark"]
            print(f"  quality benchmark: v1={qb.get('v1_count')} v2={qb.get('v2_count')}")
        print(f"\nsaved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
