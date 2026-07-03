"""RAG Fusion: несколько вариантов запроса, слияние ранкингов через RRF."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, TYPE_CHECKING

from tmki_rag.bm25 import reciprocal_rank_fusion
from tmki_rag.feature_flags import rag_fusion_llm_enabled

if TYPE_CHECKING:
    pass

_TOKEN_RE = re.compile(r"[а-яёa-z0-9]{3,}", re.IGNORECASE)


def expand_query_variants(query: str, *, max_variants: int = 4) -> list[str]:
    """Варианты запроса: оригинал, нормализация, ключевые токены, опционально Ollama."""
    q = query.strip()
    if not q:
        return []
    variants: list[str] = [q]

    from tmki_rag.retrieval import normalize_query

    norm = normalize_query(q)
    if norm and norm.lower() != q.lower():
        variants.append(norm)

    tokens = _TOKEN_RE.findall(norm or q)
    if len(tokens) >= 3:
        keywords = " ".join(tokens[:12])
        if keywords.lower() not in {v.lower() for v in variants}:
            variants.append(keywords)

    if rag_fusion_llm_enabled():
        for para in _ollama_paraphrases(q, max_extra=max(0, max_variants - len(variants))):
            if para.lower() not in {v.lower() for v in variants}:
                variants.append(para)

    return variants[:max_variants]


def _ollama_paraphrases(query: str, *, max_extra: int = 2) -> list[str]:
    if max_extra <= 0:
        return []
    base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    prompt = (
        "Перефразируй поисковый запрос по архиву инженерных документов на русском. "
        f"Исходный запрос: «{query}»\n"
        f"Верни ровно {max_extra} вариант(а), по одному на строку, без нумерации."
    )
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 120},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return []
    text = (data.get("response") or "").strip()
    if not text:
        return []
    lines = [ln.strip(" \t-•0123456789.)") for ln in text.splitlines() if ln.strip()]
    out: list[str] = []
    for line in lines:
        if len(line) < 4 or line.lower() == query.lower():
            continue
        out.append(line)
        if len(out) >= max_extra:
            break
    return out


def fuse_chunk_rankings(
    ranked_lists: list[list[dict[str, Any]]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    if not ranked_lists:
        return []
    if len(ranked_lists) == 1:
        return ranked_lists[0][:top_k]
    return reciprocal_rank_fusion(ranked_lists, top_k=top_k)
