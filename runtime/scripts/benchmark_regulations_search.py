#!/usr/bin/env python3
"""Быстрый benchmark RAG по регламентам."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_QUERIES = [
    "промбезопасность",
    "кран ростехнадзор",
    "маркшейдерская съёмка",
    "ОПО опасный производственный объект",
    "договор субаренды",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark regulations RAG search")
    parser.add_argument("--variant", choices=["auto", "v1", "v2"], default="auto")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("queries", nargs="*", default=DEFAULT_QUERIES)
    args = parser.parse_args()

    from tmki_policy import build_policy_context, load_org_snapshot
    from tmki_rag import load_regulations_chunks, rag_search, resolve_regulations_chunks_path

    try:
        path = resolve_regulations_chunks_path(args.variant)
        chunks = load_regulations_chunks(path)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    snapshot = load_org_snapshot(ROOT / "schemas/org/examples/satimol-snapshot.example.json")
    ctx = build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )

    print(f"chunks: {path} ({len(chunks)} records)\n")
    for query in args.queries:
        resp = rag_search(
            {
                "trace_id": "bench",
                "query": query,
                "policy_context": ctx,
                "top_k": args.top_k,
            },
            chunks,
        )
        n = len(resp["results"])
        preview = ""
        if n:
            preview = (resp["results"][0]["citation"].get("snippet") or "")[:120]
        print(f"Q: {query}")
        print(f"   hits={n}  top={preview!r}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
