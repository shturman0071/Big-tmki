"""Парсинг Q&A в формате Azure synthetic-qa-generation ([Q]: / [A]:)."""

from __future__ import annotations

import re
from typing import Any

_QA_PAIR_RE = re.compile(
    r"\[Q\]\s*:\s*(.*?)\s*\[A\]\s*:\s*(.*?)(?=\[Q\]\s*:|$)",
    re.DOTALL | re.IGNORECASE,
)


def parse_azure_qa_response(text: str) -> list[dict[str, str]]:
    text = (text or "").strip()
    if not text:
        return []
    pairs: list[dict[str, str]] = []
    for match in _QA_PAIR_RE.finditer(text):
        q = match.group(1).strip()
        a = match.group(2).strip()
        if q and a:
            pairs.append({"question": q, "answer": a})
    if pairs:
        return pairs
    # fallback: JSON [{"question","answer"}]
    import json

    blob = text
    if blob.startswith("```"):
        blob = blob.split("```", 2)[1]
        if blob.startswith("json"):
            blob = blob[4:]
    start, end = blob.find("["), blob.rfind("]")
    if start >= 0 and end > start:
        try:
            data = json.loads(blob[start : end + 1])
            for item in data:
                if isinstance(item, dict):
                    q = str(item.get("question") or "").strip()
                    a = str(item.get("answer") or "").strip()
                    if q and a:
                        pairs.append({"question": q, "answer": a})
        except json.JSONDecodeError:
            pass
    return pairs


def to_chat_samples(
    pairs: list[dict[str, str]],
    *,
    source_file: str = "",
    system_prompt: str = "",
    context: str = "",
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for pair in pairs:
        instruction = pair.get("question") or ""
        response = pair.get("answer") or ""
        if not instruction or not response:
            continue
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        user_content = instruction
        if context:
            user_content = f"Контекст:\n{context[:8000]}\n\nВопрос: {instruction}"
        messages.append({"role": "user", "content": user_content})
        messages.append({"role": "assistant", "content": response})
        out.append(
            {
                "source_file": source_file,
                "instruction": instruction,
                "context": context[:8000] if context else "",
                "response": response,
                "messages": messages,
            }
        )
    return out
