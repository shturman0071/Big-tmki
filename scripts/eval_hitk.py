#!/usr/bin/env python3
"""Hit@K / MRR на корпусе data/test_docs (таблица chunks, pgvector)."""

from __future__ import annotations

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME = os.path.join(ROOT, "runtime")
sys.path.insert(0, ROOT)
sys.path.insert(0, RUNTIME)

from tmki_runtime.rag_env import load_rag_config

load_rag_config(override=False)
os.environ.setdefault("TMKI_INDEX_BACKEND", "pgvector")
os.environ.setdefault("TMKI_PGVECTOR_TABLE", "chunks")

# Ground truth по реальным файлам в data/test_docs
EVAL_QUESTIONS = [
    {
        "query": "документ о качестве 452",
        "expect_any": ["качеств", "452"],
        "expect_doc": "Документ о качестве №452.pdf",
        "expect_digits": ["452"],
    },
    {
        "query": "протокол СС КС",
        "expect_any": ["протокол", "сс", "кс"],
        "expect_doc": "Протокол",
    },
    {
        "query": "замечания КМД армировка",
        "expect_any": ["замечан", "кмд", "армиров"],
        "expect_doc": "Замечания",
    },
    {
        "query": "invoice approval ПИРС",
        "expect_any": ["invoice", "approval", "пирс", "0036"],
        "expect_doc": "0036",
    },
    {
        "query": "письмо 274",
        "expect_any": ["письм", "274"],
        "expect_doc": "274",
        "expect_digits": ["274"],
    },
]


def _hay(citation: dict) -> str:
    parts = [
        citation.get("file_name") or "",
        citation.get("relative_path") or "",
        citation.get("snippet") or "",
        citation.get("doc_id") or "",
    ]
    return " ".join(parts).lower()


def _rank(citations: list[dict], expect_any: list[str]) -> int:
    needles = [e.lower() for e in expect_any]
    for i, cit in enumerate(citations, start=1):
        hay = _hay(cit)
        if any(n in hay for n in needles):
            return i
    return 0


def _strict_top_match(citations: list[dict], expect_digits: list[str]) -> bool:
    if not citations or not expect_digits:
        return True
    from tmki_rag.match_score import filename_contains_doc_number

    top = citations[0]
    name = " ".join(
        str(top.get(k) or "") for k in ("file_name", "relative_path", "doc_id")
    )
    return all(filename_contains_doc_number(name, d) for d in expect_digits)


def main() -> int:
    from tmki_demo.qa import ask_regulations

    top_k = int(os.environ.get("TMKI_EVAL_TOP_K", "5"))
    llm = os.environ.get("TMKI_EVAL_LLM", "stub")
    t0 = time.time()
    rows = []
    hits = 0
    strict_hits = 0
    rr_sum = 0.0

    for q in EVAL_QUESTIONS:
        result = ask_regulations(q["query"], llm_provider=llm, corpus_id="test_docs")
        citations = (result.get("citations") or [])[:top_k]
        rank = _rank(citations, q["expect_any"])
        hit = rank > 0
        strict = _strict_top_match(citations, q.get("expect_digits") or [])
        rr = (1.0 / rank) if rank else 0.0
        if hit:
            hits += 1
        if strict:
            strict_hits += 1
        rr_sum += rr
        rows.append(
            {
                "query": q["query"],
                "rank": rank,
                "hit": hit,
                "strict_hit": strict,
                "rr": round(rr, 3),
                "top_file": citations[0].get("file_name") if citations else "",
                "expect_doc": q.get("expect_doc", ""),
                "expect_digits": q.get("expect_digits"),
            }
        )

    n = len(EVAL_QUESTIONS)
    summary = {
        "questions": n,
        "top_k": top_k,
        "llm": llm,
        "hit_at_k": round(hits / n, 3),
        "strict_hit_at_1": round(strict_hits / n, 3),
        "mrr": round(rr_sum / n, 3),
        "elapsed_sec": round(time.time() - t0, 1),
        "rows": rows,
    }

    print(f"Hit@{top_k} eval (pgvector chunks, llm={llm})")
    print("=" * 64)
    for r in rows:
        mark = "HIT " if r["hit"] else "MISS"
        strict = "ok" if r["strict_hit"] else "WRONG_DOC#"
        print(f"  [{mark}] rank={r['rank'] or '-'}  strict={strict}  {r['query']}")
        print(f"         top: {r['top_file']}")
    print("=" * 64)
    print(
        f"Hit@{top_k}: {summary['hit_at_k']:.1%}   "
        f"Strict@1: {summary['strict_hit_at_1']:.1%}   "
        f"MRR: {summary['mrr']:.3f}   ({summary['elapsed_sec']}s)"
    )

    out = os.path.join(ROOT, "runtime", "artifacts", "eval-hitk.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"Saved: {out}")
    return 0 if strict_hits == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
