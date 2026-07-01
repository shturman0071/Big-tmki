#!/usr/bin/env python3
"""MVP run по импортированным регламентам (chunks-v2 или chunks)."""

from __future__ import annotations

import argparse
import json
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
    args = parser.parse_args()

    from tmki_policy import build_policy_context, load_org_snapshot
    from tmki_rag import VectorChunkIndex, load_regulations_chunks, resolve_regulations_chunks_path
    from tmki_runtime import run_mvp

    try:
        chunks_path = args.chunks or resolve_regulations_chunks_path(args.variant)
        chunks = load_regulations_chunks(chunks_path)
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

    index = None
    chunk_list = chunks
    use_hybrid = False
    if args.hybrid:
        index = VectorChunkIndex()
        index.add(chunks)
        chunk_list = []
        use_hybrid = True

    result = run_mvp(
        message=args.message,
        policy_context=ctx,
        chunks=chunk_list,
        index=index,
        use_hybrid_search=use_hybrid,
        llm_provider=args.llm,
    )

    print(json.dumps(result["output"], ensure_ascii=False, indent=2))
    print(f"\nchunks: {chunks_path} ({len(chunks)} records)", file=sys.stderr)
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
