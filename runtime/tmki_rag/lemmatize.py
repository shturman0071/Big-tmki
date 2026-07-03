"""Лемматизация русского текста для keyword/BM25 поиска (pymorphy3, с кешем).

Приводит слова к начальной форме: «договору/договоры/договором» → «договор».
Без pymorphy3 — безопасный fallback (нормализация регистра + ё→е)."""

from __future__ import annotations

import os
import re
from functools import lru_cache

_TOKEN_RE = re.compile(r"[а-яёa-z0-9]+", re.IGNORECASE)

_MORPH = None
_MORPH_TRIED = False


def _get_morph():
    global _MORPH, _MORPH_TRIED
    if _MORPH_TRIED:
        return _MORPH
    _MORPH_TRIED = True
    if os.environ.get("TMKI_DISABLE_LEMMATIZE") == "1":
        return None
    try:
        import pymorphy3

        _MORPH = pymorphy3.MorphAnalyzer()
    except Exception:
        _MORPH = None
    return _MORPH


@lru_cache(maxsize=100_000)
def lemmatize_word(word: str) -> str:
    w = word.lower().replace("ё", "е")
    if len(w) < 3 or w.isdigit():
        return w
    morph = _get_morph()
    if morph is None:
        return w
    try:
        parsed = morph.parse(w)
    except Exception:
        return w
    if not parsed:
        return w
    return parsed[0].normal_form.replace("ё", "е")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def lemmatize_tokens(text: str) -> list[str]:
    """Токены текста, приведённые к начальной форме."""
    return [lemmatize_word(tok) for tok in tokenize(text) if len(tok) >= 2]


def lemma_set(text: str) -> set[str]:
    return set(lemmatize_tokens(text))


def lemmatize_available() -> bool:
    return _get_morph() is not None
