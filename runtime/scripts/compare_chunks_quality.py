#!/usr/bin/env python3
"""Сравнение качества поиска chunks v1 (stub) vs v2 (local OCR)."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

QUERIES = [
    "промбезопасность",
    "кран",
    "маркшейдерская",
    "ОПО",
    "договор",
]


def _hits(chunks, ctx, query: str, top_k: int = 3) -> tuple[int, float]:
    from tmki_rag import rag_search

    resp = rag_search(
        {"trace_id": "cmp", "query": query, "policy_context": ctx, "top_k": top_k},
        chunks,
    )
    results = resp["results"]
    avg_score = sum(r["score"] for r in results) / len(results) if results else 0.0
    return len(results), avg_score


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare v1 vs v2 regulations search")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--save",
        type=Path,
        default=None,
        help="Сохранить JSON-отчёт (например artifacts/regulations-import/quality-benchmark.json)",
    )
    args = parser.parse_args()

    from tmki_policy import build_policy_context, load_org_snapshot
    from tmki_rag.chunks_io import (
        DEFAULT_REGULATIONS_CHUNKS,
        DEFAULT_REGULATIONS_CHUNKS_V2,
        load_chunks_file,
    )

    if not DEFAULT_REGULATIONS_CHUNKS.is_file():
        print("chunks.json не найден", file=sys.stderr)
        return 1

    v1 = load_chunks_file(DEFAULT_REGULATIONS_CHUNKS)
    v2 = load_chunks_file(DEFAULT_REGULATIONS_CHUNKS_V2) if DEFAULT_REGULATIONS_CHUNKS_V2.is_file() else None

    snapshot = load_org_snapshot(ROOT / "schemas/org/examples/satimol-snapshot.example.json")
    ctx = build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )

    print(f"v1: {len(v1)} chunks")
    print(f"v2: {len(v2) if v2 else 0} chunks\n")
    rows: list[dict] = []
    print(f"{'query':<25} {'v1_h':>5} {'v1_sc':>6} {'v2_h':>5} {'v2_sc':>6}")
    print("-" * 52)
    for q in QUERIES:
        h1, s1 = _hits(v1, ctx, q, args.top_k)
        h2, s2 = (_hits(v2, ctx, q, args.top_k) if v2 else (0, 0.0))
        rows.append({"query": q, "v1_hits": h1, "v1_score": s1, "v2_hits": h2, "v2_score": s2})
        print(f"{q:<25} {h1:>5} {s1:>6.3f} {h2:>5} {s2:>6.3f}")

    payload = {"v1_count": len(v1), "v2_count": len(v2 or []), "rows": rows}
    if args.json:
        import json

        print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.save:
        import json
        from datetime import datetime, timezone

        args.save.parent.mkdir(parents=True, exist_ok=True)
        out = {**payload, "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
        args.save.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"saved: {args.save}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
