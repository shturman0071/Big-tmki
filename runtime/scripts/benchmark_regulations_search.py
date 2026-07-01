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
    parser.add_argument("--backend", choices=["json", "pgvector"], default="json")
    parser.add_argument("--hybrid", action="store_true")
    parser.add_argument("queries", nargs="*", default=DEFAULT_QUERIES)
    args = parser.parse_args()

    from tmki_policy import build_policy_context, load_org_snapshot
    from tmki_rag import (
        VectorChunkIndex,
        get_chunk_index,
        hybrid_score_fn,
        load_regulations_chunks,
        rag_search,
        rag_search_with_index,
        resolve_regulations_chunks_path,
    )
    from tmki_rag.pgvector import PgVectorChunkIndex
    from tmki_rag.search import _default_score

    path = resolve_regulations_chunks_path(args.variant)
    index = None
    chunks: list = []
    score_fn = None

    if args.backend == "pgvector":
        backend = get_chunk_index()
        if not isinstance(backend, PgVectorChunkIndex):
            print("pgvector недоступен", file=sys.stderr)
            return 1
        index = backend
        if args.hybrid:
            score_fn = hybrid_score_fn(index, _default_score)
        print(f"backend: pgvector ({index.count()} rows)\n")
    else:
        try:
            chunks = load_regulations_chunks(path)
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"chunks: {path} ({len(chunks)} records)\n")
        if args.hybrid:
            index = VectorChunkIndex()
            index.add(chunks)
            chunks = []
            score_fn = hybrid_score_fn(index, _default_score)

    snapshot = load_org_snapshot(ROOT / "schemas/org/examples/satimol-snapshot.example.json")
    ctx = build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )

    for query in args.queries:
        req = {
            "trace_id": "bench",
            "query": query,
            "policy_context": ctx,
            "top_k": args.top_k,
        }
        if index is not None:
            resp = rag_search_with_index(req, index, score_fn=score_fn)
        else:
            resp = rag_search(req, chunks)
        n = len(resp["results"])
        preview = ""
        if n:
            preview = (resp["results"][0]["citation"].get("snippet") or "")[:120]
        print(f"Q: {query}")
        print(f"   hits={n}  top={preview!r}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
