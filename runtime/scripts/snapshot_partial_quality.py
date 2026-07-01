#!/usr/bin/env python3
"""Partial quality benchmark на текущем chunks-v2 (read-only для re-index)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "reindex-state.json"
)
DEFAULT_HEARTBEAT = DEFAULT_STATE.parent / "reindex-heartbeat.json"
DEFAULT_LOCK = DEFAULT_STATE.parent / "reindex.lock"
QUERIES = ["промбезопасность", "кран", "маркшейдерская", "ОПО", "договор"]


def _run_v2_hybrid_benchmark(top_k: int = 3) -> dict:
    from tmki_policy import build_policy_context, load_org_snapshot
    from tmki_rag import VectorChunkIndex, hybrid_score_fn, rag_search_with_index
    from tmki_rag.chunks_io import DEFAULT_REGULATIONS_CHUNKS_V2, load_chunks_file
    from tmki_rag.search import _default_score

    if not DEFAULT_REGULATIONS_CHUNKS_V2.is_file():
        raise FileNotFoundError(f"chunks-v2 не найден: {DEFAULT_REGULATIONS_CHUNKS_V2}")

    v2 = load_chunks_file(DEFAULT_REGULATIONS_CHUNKS_V2)
    snapshot = load_org_snapshot(ROOT / "schemas/org/examples/satimol-snapshot.example.json")
    ctx = build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )
    index = VectorChunkIndex()
    index.add(v2)
    score_fn = hybrid_score_fn(index, _default_score)

    rows = []
    for q in QUERIES:
        resp = rag_search_with_index(
            {"trace_id": "partial", "query": q, "policy_context": ctx, "top_k": top_k},
            index,
            score_fn=score_fn,
        )
        n = len(resp["results"])
        avg = sum(r["score"] for r in resp["results"]) / n if n else 0.0
        rows.append({"query": q, "hits": n, "avg_score": avg})

    return {"v2_count": len(v2), "hybrid": True, "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="Partial v2 hybrid quality snapshot")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--save", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.state.is_file():
        print(f"state не найден: {args.state}", file=sys.stderr)
        return 1

    from tmki_ingest.quality_snapshot import write_partial_quality_snapshot
    from tmki_ingest.reindex_progress import build_reindex_report

    report = build_reindex_report(
        state_path=args.state,
        heartbeat_path=args.heartbeat,
        lock_path=args.lock,
    )
    if report.get("complete"):
        print("re-index завершён — используйте compare_chunks_quality / finalize", file=sys.stderr)
        return 2

    try:
        payload = _run_v2_hybrid_benchmark()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    pct = int(report.get("percent") or 0)
    out = args.save or (args.state.parent / f"quality-partial-p{pct}.json")
    latest = args.state.parent / "quality-partial-latest.json"
    write_partial_quality_snapshot(save_path=out, report=report, payload=payload)
    write_partial_quality_snapshot(save_path=latest, report=report, payload=payload)

    if args.json:
        print(json.dumps(json.loads(out.read_text(encoding="utf-8")), ensure_ascii=False, indent=2))
    else:
        print(f"partial quality saved: {out}", file=sys.stderr)
        print(f"  progress: {report['live_progress']}/{report['total']} ({report['percent']}%)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
