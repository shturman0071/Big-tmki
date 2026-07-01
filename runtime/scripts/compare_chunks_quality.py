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


def _hits(chunks, ctx, query: str, top_k: int = 3) -> int:
    from tmki_rag import rag_search

    resp = rag_search(
        {"trace_id": "cmp", "query": query, "policy_context": ctx, "top_k": top_k},
        chunks,
    )
    return len(resp["results"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare v1 vs v2 regulations search")
    parser.add_argument("--top-k", type=int, default=3)
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
    print(f"{'query':<25} {'v1':>5} {'v2':>5}")
    print("-" * 38)
    for q in QUERIES:
        h1 = _hits(v1, ctx, q, args.top_k)
        h2 = _hits(v2, ctx, q, args.top_k) if v2 else 0
        print(f"{q:<25} {h1:>5} {h2:>5}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
