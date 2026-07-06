"""Оценка совпадения запроса с текстом: точное написание → регистр → леммы."""

from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"[а-яёa-z0-9]{2,}", re.IGNORECASE)

_KMD_MARK_QUERY = re.compile(
    r"ограждени[ея]\s*(?:№|#)?\s*(\d+)\b",
    re.IGNORECASE,
)


def significant_query_tokens(query: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall((query or "").strip()) if len(t) >= 2]


_OCR_ALIASES: dict[str, tuple[str, ...]] = {
    "проминвест": ("nponisusecr", "nponinvest", "nponis"),
}


def ocr_alias_tokens() -> frozenset[str]:
    out: set[str] = set()
    for aliases in _OCR_ALIASES.values():
        out.update(aliases)
    return frozenset(out)


def _token_in_text(token: str, raw_lower: str) -> bool:
    if token in raw_lower:
        return True
    for alias in _OCR_ALIASES.get(token, ()):
        if alias in raw_lower:
            return True
    return False


def split_required_optional_tokens(query: str, corpus_text: str) -> tuple[list[str], list[str]]:
    """Токены, отсутствующие в корпусе, не блокируют поиск (например, опечатка или имя вне OCR)."""
    tokens = [t for t in significant_query_tokens(query) if t not in ocr_alias_tokens()]
    if len(tokens) < 2 or not corpus_text:
        return tokens, []
    blob = corpus_text.lower()
    required: list[str] = []
    optional: list[str] = []
    for token in tokens:
        if _token_in_text(token, blob):
            required.append(token)
        else:
            optional.append(token)
    if not required:
        return tokens, []
    return required, optional


def any_query_token_in_text(query: str, text: str) -> bool:
    tokens = significant_query_tokens(query)
    if not tokens or not text:
        return False
    raw_lower = text.lower()
    return any(_token_in_text(t, raw_lower) for t in tokens)


def all_query_tokens_in_text(
    query: str,
    text: str,
    *,
    lemma_set_fn=None,
) -> bool:
    """Все значимые слова запроса есть в тексте (буквально или по леммам)."""
    tokens = significant_query_tokens(query)
    if not tokens or not text:
        return False
    raw_lower = text.lower()
    if all(_token_in_text(t, raw_lower) for t in tokens):
        return True
    if lemma_set_fn is None:
        from tmki_rag.lemmatize import lemma_set as _lemma_set

        def lemma_set_fn(t: str) -> set[str]:
            return _lemma_set(t)

    from tmki_rag.lemmatize import lemmatize_tokens

    q_lemmas = lemmatize_tokens(query)
    if not q_lemmas:
        return False
    doc_lemmas = lemma_set_fn(raw_lower)
    return all(lem in doc_lemmas for lem in q_lemmas)


def text_match_score(query: str, text: str, *, lemma_set_fn=None) -> float:
    """
    Приоритет (как в поиске Windows + морфология):
    1.0  — фраза в документе **как в запросе** (регистр и орфография)
    0.93 — та же фраза, другой регистр
    0.88 — все слова с **точным написанием** и тем же регистром
    0.80 — все слова с точным написанием, регистр не важен
    0.50–0.79 — часть слов по точному написанию
    0.35–0.72 — совпадение по леммам (другой падеж), ниже точного
    """
    q = (query or "").strip()
    raw = text or ""
    if not q or not raw:
        return 0.0

    if q in raw:
        return 1.0

    q_lower = q.lower()
    raw_lower = raw.lower()
    if q_lower in raw_lower:
        return 0.93

    mark_q = _KMD_MARK_QUERY.search(q)
    if mark_q:
        num = mark_q.group(1)
        remark = re.search(
            rf"ограждени[ея]\s*ог-{re.escape(num)}/([^/\n]{{1,80}})",
            raw_lower,
        )
        if remark:
            tail = remark.group(1)
            if "замечаний нет" not in tail and len(tail.strip()) > 3:
                return 1.0
            return 0.85
        if re.search(rf"ог-{re.escape(num)}(?:\b|/)", raw_lower):
            return 0.96

    tokens_query = [t for t in _TOKEN_RE.findall(q)]
    tokens_lower = [t.lower() for t in tokens_query]
    if not tokens_lower:
        return 0.0

    if all(t in raw_lower for t in tokens_lower):
        case_exact = sum(1 for t in tokens_query if t in raw)
        if case_exact == len(tokens_query):
            return 0.88
        return 0.80 + 0.06 * (case_exact / len(tokens_query))

    literal_hits = sum(1 for t in tokens_lower if t in raw_lower)
    if len(tokens_lower) >= 2 and literal_hits < len(tokens_lower):
        lemma_score = 0.0
        if lemma_set_fn is None:
            from tmki_rag.lemmatize import lemma_set as _lemma_set

            def lemma_set_fn(t: str) -> set[str]:
                return _lemma_set(t)
        from tmki_rag.lemmatize import lemmatize_tokens

        q_lemmas = lemmatize_tokens(q)
        if q_lemmas:
            doc_lemmas = lemma_set_fn(raw_lower)
            lemma_hits = sum(1 for lem in q_lemmas if lem in doc_lemmas)
            if lemma_hits == len(q_lemmas):
                return 0.74 + 0.06 * (lemma_hits / len(q_lemmas))
        coverage = literal_hits / len(tokens_lower)
        return min(0.52, 0.28 + 0.24 * coverage)

    literal_score = 0.0
    if literal_hits:
        literal_score = 0.50 + 0.29 * (literal_hits / len(tokens_lower))

    if lemma_set_fn is None:
        from tmki_rag.lemmatize import lemma_set as _lemma_set

        def lemma_set_fn(t: str) -> set[str]:
            return _lemma_set(t)

    from tmki_rag.lemmatize import lemmatize_tokens

    q_lemmas = lemmatize_tokens(q)
    lemma_score = 0.0
    if q_lemmas:
        doc_lemmas = lemma_set_fn(raw_lower)
        lemma_hits = sum(1 for lem in q_lemmas if lem in doc_lemmas)
        if lemma_hits:
            lemma_score = 0.35 + 0.37 * (lemma_hits / len(q_lemmas))

    if literal_score >= lemma_score:
        return min(0.79, literal_score)
    return min(0.72, lemma_score)


_DOC_NUM_RE_CACHE: dict[str, re.Pattern[str]] = {}


def filename_contains_doc_number(filename: str, number: str) -> bool:
    """Номер документа в имени файла (№452, _452), не подстрока внутри другого числа."""
    if not filename or not number:
        return False
    if number not in _DOC_NUM_RE_CACHE:
        _DOC_NUM_RE_CACHE[number] = re.compile(
            rf"(?:№|#|\b){re.escape(number)}(?:\b|\.|_|-)",
            re.IGNORECASE,
        )
    return bool(_DOC_NUM_RE_CACHE[number].search(filename))


def citation_doc_number_score(citation: dict[str, Any], query_numbers: list[str]) -> int:
    """Бонус/штраф для переранжирования цитат по номеру в имени файла."""
    import re

    name = " ".join(
        str(citation.get(k) or "")
        for k in ("file_name", "relative_path", "doc_id")
    )
    if not name or not query_numbers:
        return 0
    score = 0
    for num in query_numbers:
        if filename_contains_doc_number(name, num):
            score += 100
    for found in re.findall(r"\d{2,}", name):
        if found not in query_numbers:
            score -= 40
    return score
