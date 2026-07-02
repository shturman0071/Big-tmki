#!/usr/bin/env python3
"""Прогон демо-вопросов для руководства (stub или ollama)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

LEADERSHIP_DEMO_QUESTIONS: list[dict[str, str]] = [
    {"label": "Кран / Ростехнадзор", "query": "кран ростехнадзор", "intent": "qa"},
    {"label": "ОПО", "query": "ОПО опасный производственный объект", "intent": "qa"},
    {"label": "Промбезопасность", "query": "промбезопасность", "intent": "qa"},
    {"label": "Маркшейдерская съёмка", "query": "требования к маркшейдерской съемке", "intent": "qa"},
    {"label": "Охрана труда", "query": "охрана труда на участке", "intent": "qa"},
    {"label": "Пожарная безопасность", "query": "инструкция по пожарной безопасности", "intent": "qa"},
    {"label": "Инструктаж", "query": "порядок проведения инструктажа по охране труда", "intent": "qa"},
    {"label": "Открыть документ", "query": "открой акт маркшейдерской опорной сети", "intent": "open"},
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Leadership Q&A benchmark over regulations")
    parser.add_argument("--llm", default=None, choices=["stub", "ollama", "openai"])
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--limit", type=int, default=0, help="Max questions (0 = all)")
    args = parser.parse_args()

    os.environ.setdefault("TMKI_INDEX_BACKEND", "json")
    from tmki_demo.qa import ask_regulations, resolve_llm_provider

    llm = args.llm or resolve_llm_provider()
    items = LEADERSHIP_DEMO_QUESTIONS[: args.limit] if args.limit else LEADERSHIP_DEMO_QUESTIONS
    report: list[dict[str, object]] = []

    print(f"Leadership Q&A benchmark ({len(items)} questions, llm={llm})")
    print("=" * 60)

    for item in items:
        query = item["query"]
        result = ask_regulations(query, llm_provider=llm)
        citations = result.get("citations") or []
        first = citations[0] if citations else {}
        snippet = (first.get("snippet") or "")[:140]
        file_name = first.get("file_name") or ""
        row = {
            "label": item["label"],
            "query": query,
            "expected_intent": item["intent"],
            "intent": result.get("intent"),
            "confidence": result.get("confidence"),
            "citation_count": len(citations),
            "top_file": file_name,
            "top_snippet": snippet,
            "answer_preview": (result.get("answer") or "")[:240],
            "backend": result.get("backend"),
            "index_rows": result.get("index_rows"),
        }
        report.append(row)

        if args.json:
            continue
        ok_intent = "OK" if row["intent"] == item["intent"] else "MISMATCH"
        cit_ok = "OK" if citations else "NO_CIT"
        print(f"\n[{item['label']}] {query}")
        print(f"  intent: {row['intent']} ({ok_intent})  citations: {len(citations)} ({cit_ok})  conf={row['confidence']}")
        if file_name:
            print(f"  file: {file_name}")
        if snippet:
            print(f"  snippet: {snippet}")
        print(f"  answer: {row['answer_preview']}")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        passed = sum(1 for r, q in zip(report, items) if r["intent"] == q["intent"] and r["citation_count"])
        print("\n" + "=" * 60)
        print(f"Summary: {passed}/{len(items)} with expected intent and ≥1 citation")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
