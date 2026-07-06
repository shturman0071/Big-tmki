"""Recursive Language Model (RLM) — пошаговое извлечение из CTX без полной загрузки в контекст."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

_EXCERPT_ID_RE = re.compile(r'"excerpt_ids"\s*:\s*\[([^\]]*)\]')


@dataclass(frozen=True)
class CtxChunk:
    chunk_id: int
    text: str
    start: int
    end: int


def chunk_ctx(text: str, *, chunk_size: int = 2400, overlap: int = 200) -> list[CtxChunk]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [CtxChunk(0, text, 0, len(text))]
    chunks: list[CtxChunk] = []
    pos = 0
    cid = 0
    while pos < len(text):
        end = min(len(text), pos + chunk_size)
        piece = text[pos:end].strip()
        if piece:
            chunks.append(CtxChunk(cid, piece, pos, end))
            cid += 1
        if end >= len(text):
            break
        pos = max(0, end - overlap)
    return chunks


def _format_ctx_index(chunks: list[CtxChunk], *, preview_chars: int = 400) -> str:
    lines: list[str] = []
    for ch in chunks:
        preview = ch.text[:preview_chars]
        if len(ch.text) > preview_chars:
            preview += "…"
        lines.append(f"[{ch.chunk_id}] chars {ch.start}-{ch.end}:\n{preview}")
    return "\n\n".join(lines)


def _parse_excerpt_ids(raw: str) -> list[int]:
    match = _EXCERPT_ID_RE.search(raw)
    if not match:
        return []
    inner = match.group(1)
    ids: list[int] = []
    for part in inner.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


def _call_ollama(*, system: str, user: str, model: str) -> str:
    import os
    import urllib.request

    base = os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OLLAMA_URL") or "http://127.0.0.1:11434"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }
    req = urllib.request.Request(
        f"{base.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return (data.get("message") or {}).get("content", "").strip()


def select_excerpts(
    *,
    question: str,
    chunks: list[CtxChunk],
    model: str,
    system_prompt: str,
    max_rounds: int = 2,
) -> list[CtxChunk]:
    if not chunks:
        return []
    if len(chunks) == 1:
        return chunks

    index = _format_ctx_index(chunks)
    selected: list[CtxChunk] = []
    seen: set[int] = set()

    for round_no in range(max_rounds):
        user = (
            f"Вопрос: {question}\n\n"
            f"CTX index ({len(chunks)} фрагментов, полный текст НЕ показан):\n{index}\n\n"
            "Выбери excerpt_ids релевантных фрагментов (JSON)."
        )
        if selected:
            user += f"\nУже выбрано: {sorted(seen)}. Нужны дополнительные фрагменты?"

        raw = _call_ollama(system=system_prompt, user=user, model=model)
        ids = _parse_excerpt_ids(raw)
        if not ids:
            # keyword fallback
            q_tokens = {t for t in re.findall(r"[а-яёa-z0-9]{4,}", question.lower())}
            scored: list[tuple[int, CtxChunk]] = []
            for ch in chunks:
                text_l = ch.text.lower()
                score = sum(1 for t in q_tokens if t in text_l)
                scored.append((score, ch))
            scored.sort(key=lambda x: x[0], reverse=True)
            ids = [ch.chunk_id for _, ch in scored[:3] if _ > 0]
        if not ids:
            ids = [0]

        for i in ids:
            if i < 0 or i >= len(chunks) or i in seen:
                continue
            seen.add(i)
            selected.append(chunks[i])
        if len(selected) >= 3 or round_no == max_rounds - 1:
            break

    return selected or [chunks[0]]


def rlm_answer(
    *,
    ctx: str,
    question: str,
    model: str | None = None,
    chunk_size: int = 2400,
    max_rounds: int = 2,
) -> dict[str, Any]:
    import os

    from tmki_runtime.prompt_catalog import load_task_prompt

    model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    system = load_task_prompt("rlm_system")
    chunks = chunk_ctx(ctx, chunk_size=chunk_size)
    picked = select_excerpts(
        question=question,
        chunks=chunks,
        model=model,
        system_prompt=system,
        max_rounds=max_rounds,
    )
    excerpts = "\n\n---\n\n".join(f"[excerpt {ch.chunk_id}]\n{ch.text}" for ch in picked)
    user = (
        f"Вопрос: {question}\n\n"
        f"Извлечённые фрагменты CTX:\n{excerpts}\n\n"
        "Дай точный ответ по фрагментам. Без выдумок."
    )
    answer = _call_ollama(system=system, user=user, model=model)
    return {
        "answer": answer,
        "excerpt_ids": [ch.chunk_id for ch in picked],
        "chunks_total": len(chunks),
        "model": model,
        "mode": "rlm",
    }
