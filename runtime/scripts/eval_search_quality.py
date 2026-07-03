#!/usr/bin/env python3
"""Eval-гарнесс качества поиска: Hit@K и MRR на наборе вопросов.

Метрики (паттерн tim-ponomarev/hybrid-rag, acuity-rag):
  - Hit@K: доля вопросов, где релевантный документ попал в топ-K.
  - MRR:   средний обратный ранг первого релевантного результата.

«Релевантность» проверяется по ключевым словам, которые ДОЛЖНЫ встретиться
в имени файла или сниппете найденного фрагмента (ground truth без ручной
разметки chunk_id — устойчиво к пересборке индекса).

Использование:
  python scripts/eval_search_quality.py                 # текстовый отчёт
  python scripts/eval_search_quality.py --json          # JSON
  python scripts/eval_search_quality.py --save eval.json # сохранить историю
  python scripts/eval_search_quality.py --top-k 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

# Ground truth: любое из expect_any (нижний регистр) должно быть в
# имени файла или сниппете хотя бы одного из топ-K результатов.
EVAL_QUESTIONS: list[dict] = [
    {"query": "требования к маркшейдерской съемке", "expect_any": ["маркшейд", "съемк", "съёмк"]},
    {"query": "опасный производственный объект ОПО", "expect_any": ["опо", "опасн", "производствен"]},
    {"query": "промышленная безопасность кран", "expect_any": ["кран", "безопасн", "подъемн", "подъёмн"]},
    {"query": "охрана труда на участке", "expect_any": ["охран", "труд"]},
    {"query": "пожарная безопасность инструкция", "expect_any": ["пожарн", "безопасн"]},
    {"query": "порядок проведения инструктажа", "expect_any": ["инструктаж", "инструкц"]},
    {"query": "акт приема передачи опорной сети", "expect_any": ["акт", "опорн", "сет"]},
    {"query": "план ликвидации аварий", "expect_any": ["ликвидац", "авар", "план"]},
    {"query": "электроснабжение горных выработок", "expect_any": ["электро", "снабжен", "выработ"]},
    {"query": "проект производства работ", "expect_any": ["проект", "производств", "ппр"]},
]


def _hay(citation: dict) -> str:
    parts = [
        citation.get("file_name") or "",
        citation.get("relative_path") or "",
        citation.get("snippet") or "",
    ]
    return " ".join(parts).lower()


def _rank_of_relevant(citations: list[dict], expect_any: list[str]) -> int:
    """1-based ранг первого релевантного результата, или 0 если нет."""
    needles = [e.lower() for e in expect_any]
    for i, cit in enumerate(citations, start=1):
        hay = _hay(cit)
        if any(n in hay for n in needles):
            return i
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Search quality eval (Hit@K, MRR)")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--llm", default="stub", choices=["stub", "ollama", "openai"])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--save", type=Path, default=None, help="append run to JSON history file")
    args = parser.parse_args()

    import os

    os.environ.setdefault("TMKI_INDEX_BACKEND", "json")
    from tmki_demo.qa import ask_regulations

    rows: list[dict] = []
    hits = 0
    rr_sum = 0.0
    t0 = time.time()

    for q in EVAL_QUESTIONS:
        result = ask_regulations(q["query"], llm_provider=args.llm)
        citations = (result.get("citations") or [])[: args.top_k]
        rank = _rank_of_relevant(citations, q["expect_any"])
        hit = rank > 0
        rr = (1.0 / rank) if rank else 0.0
        if hit:
            hits += 1
        rr_sum += rr
        top_file = citations[0].get("file_name") if citations else ""
        rows.append(
            {
                "query": q["query"],
                "rank": rank,
                "hit": hit,
                "rr": round(rr, 3),
                "citations": len(citations),
                "top_file": top_file,
            }
        )

    n = len(EVAL_QUESTIONS)
    summary = {
        "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "questions": n,
        "top_k": args.top_k,
        "llm": args.llm,
        "hit_at_k": round(hits / n, 3),
        "mrr": round(rr_sum / n, 3),
        "elapsed_sec": round(time.time() - t0, 1),
        "rows": rows,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Search quality eval ({n} questions, top_k={args.top_k}, llm={args.llm})")
        print("=" * 64)
        for r in rows:
            mark = "HIT " if r["hit"] else "MISS"
            print(f"  [{mark}] rank={r['rank'] or '-'}  {r['query']}")
            if r["top_file"]:
                print(f"         top: {r['top_file']}")
        print("=" * 64)
        print(f"Hit@{args.top_k}: {summary['hit_at_k']:.1%}   MRR: {summary['mrr']:.3f}   ({summary['elapsed_sec']}s)")

    if args.save:
        history = []
        if args.save.is_file():
            try:
                history = json.loads(args.save.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                history = []
        if not isinstance(history, list):
            history = []
        history.append(summary)
        args.save.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved run to {args.save} (history: {len(history)} runs)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
