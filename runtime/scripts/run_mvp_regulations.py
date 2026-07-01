#!/usr/bin/env python3
"""MVP run по импортированным регламентам (chunks-v2 или chunks)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description="TMKI MVP over regulations chunks")
    parser.add_argument("message", nargs="?", default="промбезопасность кран")
    parser.add_argument("--variant", choices=["auto", "v1", "v2"], default="auto")
    parser.add_argument("--llm", default="stub", choices=["stub", "ollama", "openai"])
    parser.add_argument("--hybrid", action="store_true", help="vector+keyword scoring")
    parser.add_argument("--chunks", type=Path, default=None)
    parser.add_argument(
        "--backend",
        choices=["json", "pgvector", "auto"],
        default="json",
        help="json — chunks file; pgvector — DATABASE_URL; auto — env TMKI_INDEX_BACKEND",
    )
    args = parser.parse_args()

    from tmki_policy import build_policy_context, load_org_snapshot
    from tmki_rag import VectorChunkIndex, get_chunk_index, load_regulations_chunks, resolve_regulations_chunks_path
    from tmki_rag.pgvector import PgVectorChunkIndex
    from tmki_runtime import run_mvp

    use_pgvector = args.backend == "pgvector" or (
        args.backend == "auto" and os.environ.get("TMKI_INDEX_BACKEND", "").lower() == "pgvector"
    )

    chunks_path = None
    chunks = []
    index = None
    use_hybrid = False

    if use_pgvector:
        backend = get_chunk_index()
        if not isinstance(backend, PgVectorChunkIndex):
            print("pgvector недоступен: задайте DATABASE_URL и pip install -e '.[pgvector]'", file=sys.stderr)
            return 1
        index = backend
        if not index.count():
            print("pgvector пуст — сначала load_regulations_pgvector.py", file=sys.stderr)
            return 1
        chunks_path = resolve_regulations_chunks_path(args.variant)
        use_hybrid = args.hybrid or True
    else:
        try:
            chunks_path = args.chunks or resolve_regulations_chunks_path(args.variant)
            chunks = load_regulations_chunks(chunks_path)
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if args.hybrid:
            index = VectorChunkIndex()
            index.add(chunks)
            chunks = []
            use_hybrid = True

    snapshot = load_org_snapshot(ROOT / "schemas/org/examples/satimol-snapshot.example.json")
    ctx = build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )

    chunk_list: list = []
    if not use_pgvector:
        chunk_list = chunks

    result = run_mvp(
        message=args.message,
        policy_context=ctx,
        chunks=chunk_list,
        index=index,
        use_hybrid_search=use_hybrid,
        llm_provider=args.llm,
    )

    print(json.dumps(result["output"], ensure_ascii=False, indent=2))
    if use_pgvector and index is not None:
        print(f"\nbackend: pgvector ({index.count()} rows)", file=sys.stderr)
    else:
        n = len(chunks) if chunks else (len(index.list()) if index else 0)
        print(f"\nchunks: {chunks_path} ({n} records)", file=sys.stderr)
    loop_state = result["loop_state"]["loop_state"]
    print(f"loop: {loop_state}", file=sys.stderr)
    if not result["output"]:
        if args.llm == "ollama":
            print(
                "Подсказка: Ollama недоступна или модель не скачана. "
                "Проверьте: ollama --version && ollama list && ollama pull qwen2.5:7b\n"
                "Или запустите без --llm ollama (режим stub).",
                file=sys.stderr,
            )
        else:
            print("LLM-шаг не завершён. См. audit_events в run_mvp.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
