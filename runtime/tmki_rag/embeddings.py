from __future__ import annotations

import math
import re


def text_embedding(text: str, *, dims: int = 64) -> list[float]:
    """Детерминированный bag-of-words embedding (MVP до реальной модели)."""
    vec = [0.0] * dims
    tokens = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]{3,}", (text or "").lower())
    if not tokens:
        return vec
    for token in tokens:
        bucket = hash(token) % dims
        vec[bucket] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
