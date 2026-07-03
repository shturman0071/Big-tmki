"""Улучшения retrieval для регламентов: качество фрагментов, rerank, intent."""

from __future__ import annotations

import re
from typing import Any, Callable

_OPEN_INTENT = re.compile(
    r"(?:^|\b)(?:открой|открыть|найди\s+файл|найти\s+файл|покажи\s+документ|"
    r"где\s+(?:лежит|находится)|путь\s+к\s+файлу|путь\s+к\s+документу|"
    r"open|find\s+file|show\s+document)(?:\b|$)",
    re.IGNORECASE,
)

_FILENAME_QUERY = re.compile(
    r"(?:"
    r"\.(?:docx?|pdf|xls(?:x)?|msg)\b|"
    r"[_/\\]|"
    r"замечания[_\s\-]*кмд|"
    r"кс\s*\d{4,}|"
    r"кс\d{4,}|"
    r"\d{4,}[-_]\s*кмд"
    r")",
    re.IGNORECASE,
)

_COORD_NOISE = re.compile(r"^\s*[\d\s.,\-+]+(?:\s*[\d\s.,\-+]+)*\s*$")
_TOKEN_RE = re.compile(r"[а-яёa-z0-9]{3,}", re.IGNORECASE)


_CONTENT_SUMMARY = re.compile(
    r"(?:"
    r"опиши|описать|описание|"
    r"кратко|краткое|краткий|"
    r"содержание|суть|резюме|пересказ|"
    r"о\s+ч[её]м|"
    r"текст\s+(?:письма|документа|замечаний|акта)|"
    r"что\s+(?:в|написано|говорится)\s+(?:в|по)"
    r")",
    re.IGNORECASE,
)


def detect_query_intent(query: str) -> str:
    """qa — ответ по содержанию; open — найти/открыть файл; summarize — пересказ текста."""
    q = query.strip()
    if _OPEN_INTENT.search(q) and not looks_like_content_summary_query(q):
        return "open"
    if looks_like_content_summary_query(q):
        return "summarize"
    return "qa"


def looks_like_content_summary_query(query: str) -> bool:
    """Пользователь просит пересказ/содержание, а не просто путь к файлу."""
    q = query.strip()
    if not q:
        return False
    return bool(_CONTENT_SUMMARY.search(q))


def looks_like_filename_query(query: str) -> bool:
    """Запрос похож на имя файла или шифр чертежа (КМД, КС18105, …)."""
    q = query.strip()
    if not q or len(q) < 4:
        return False
    if _FILENAME_QUERY.search(q):
        return True
    tokens = _TOKEN_RE.findall(q)
    digitish = sum(1 for t in tokens if any(ch.isdigit() for ch in t))
    return digitish >= 2 and len(tokens) <= 10


def normalize_query(query: str) -> str:
    """Лёгкая нормализация инженерных запросов (без LLM)."""
    q = " ".join(query.split())
    replacements = {
        "ростех надзор": "ростехнадзор",
        "ро технадзор": "ростехнадзор",
        " ртн ": " ростехнадзор ",
        "опо ": "опасный производственный объект ",
        "пром безопасность": "промбезопасность",
        "маркшейдерскую": "маркшейдерская",
        "маркшейдерской": "маркшейдерская",
        "маркшейдерскую съемку": "маркшейдерская съемка",
        "маркшейдерской съемке": "маркшейдерская съемка",
        "работ повышенной опасности": "работы повышенной опасности",
        "инструктаж по охране": "инструктаж охрана труда",
        "пожарной безопасности": "пожарная безопасность",
    }
    # OCR-алиасы (сканы: латиница вместо кириллицы)
    _OCR_ALIASES = {
        "проминвест": "nponisusecr nponinvest",
    }
    lowered = q.lower()
    for src, dst in replacements.items():
        if src in lowered:
            q = re.sub(re.escape(src), dst, q, flags=re.IGNORECASE)
    for src, dst in _OCR_ALIASES.items():
        if src in lowered:
            q = f"{q} {dst}"
    q = _expand_kmd_mark_query(q)
    return q.strip()


_KMD_MARK_QUERY = re.compile(
    r"(ограждени[ея]|лестниц[аы]|калитк[аи]|козыр[её]к[аи]|люк[аи]|"
    r"задвижк[аи]|расстрел[аы]|уголок[аи]|пластин[аы])\s*(?:№|#)?\s*(\d+)\b",
    re.IGNORECASE,
)

_KMD_MARK_ALIASES: dict[str, str] = {
    "ограждени": "Ог",
    "ограждения": "Ог",
    "лестниц": "Л",
    "лестницы": "Л",
    "калитк": "К",
    "калитки": "К",
    "козырек": "Кн",
    "козырька": "Кн",
    "козырьки": "Кн",
    "люк": "Л",
    "люки": "Л",
    "задвижк": "З",
    "задвижки": "З",
    "расстрел": "Расстрел",
    "расстрелы": "Расстрел",
    "уголок": "Уг",
    "уголка": "Уг",
    "уголки": "Уг",
    "пластин": "П",
    "пластины": "П",
}


def _expand_kmd_mark_query(q: str) -> str:
    """«ограждение 1» → добавить «Ограждение Ог-1» (марка КМД)."""
    m = _KMD_MARK_QUERY.search(q)
    if not m:
        return q
    kind_raw, num = m.group(1), m.group(2)
    kind_lower = kind_raw.lower()
    prefix = None
    for key, pfx in _KMD_MARK_ALIASES.items():
        if kind_lower.startswith(key):
            prefix = pfx
            break
    if not prefix:
        return q
    if kind_lower.startswith("огражден"):
        phrase = f"Ограждение {prefix}-{num}"
    else:
        phrase = f"{prefix}-{num}"
    if phrase.lower() not in q.lower():
        q = f"{q} {phrase}"
    return q


def _cyrillic_ratio(text: str) -> float:
    if not text:
        return 0.0
    cyr = sum("а" <= ch.lower() <= "я" or ch.lower() == "ё" for ch in text)
    return cyr / len(text)


def _digit_ratio(text: str) -> float:
    if not text:
        return 0.0
    return sum(ch.isdigit() for ch in text) / len(text)


def chunk_text_quality(text: str) -> float:
    """
    0..1: насколько фрагмент похож на осмысленный текст регламента.
    Отсекает координаты, таблицы чисел, пустые OCR-заглушки.
    """
    preview = (text or "").strip()
    if not preview or preview == "Документ TMKI: stub OCR content.":
        return 0.0
    if len(preview) < 24:
        return 0.15
    if _COORD_NOISE.match(preview[:120]):
        return 0.05
    cyr = _cyrillic_ratio(preview)
    digits = _digit_ratio(preview)
    if digits > 0.55 and cyr < 0.08:
        return 0.1
    if cyr < 0.12 and digits > 0.25:
        return 0.2
    score = 0.35 + min(cyr, 0.55) + min(len(preview) / 400.0, 0.25)
    if digits > 0.4:
        score -= 0.15
    return max(0.0, min(1.0, score))


def keyword_overlap(query: str, text: str) -> float:
    from tmki_rag.match_score import text_match_score

    return text_match_score(query, text)


def rerank_results(query: str, results: list[dict[str, Any]], *, top_k: int = 8) -> list[dict[str, Any]]:
    """Переранжировать RAG-результаты: качество текста + пересечение с запросом."""
    from tmki_rag.match_score import all_query_tokens_in_text, significant_query_tokens

    if not results:
        return []
    require_all = len(significant_query_tokens(query)) >= 2
    scored: list[tuple[float, dict[str, Any]]] = []
    seen_docs: set[str] = set()
    for item in results:
        citation = item.get("citation") or {}
        snippet = citation.get("snippet") or item.get("content_preview") or ""
        if require_all and not all_query_tokens_in_text(query, snippet):
            continue
        base = float(item.get("score") or 0.0)
        quality = chunk_text_quality(snippet)
        if quality < 0.12:
            continue
        overlap = keyword_overlap(query, snippet)
        doc_id = item.get("doc_id") or citation.get("doc_id") or ""
        diversity_penalty = 0.08 if doc_id and doc_id in seen_docs else 0.0
        if doc_id:
            seen_docs.add(doc_id)
        final = base * (0.45 + 0.55 * quality) + 0.35 * overlap - diversity_penalty
        scored.append((final, {**item, "score": round(final, 4)}))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_k]]


def group_results_by_document(results: list[dict[str, Any]], *, limit: int = 8) -> list[dict[str, Any]]:
    """Один лучший фрагмент на документ — удобно для «найти документ по тексту»."""
    best: dict[str, dict[str, Any]] = {}
    for item in results:
        doc_id = item.get("doc_id") or (item.get("citation") or {}).get("doc_id") or ""
        if not doc_id:
            continue
        prev = best.get(doc_id)
        if prev is None or float(item.get("score") or 0) > float(prev.get("score") or 0):
            best[doc_id] = item
    ranked = sorted(best.values(), key=lambda x: float(x.get("score") or 0), reverse=True)
    return ranked[:limit]


def quality_aware_score_fn(
    base_score_fn: Callable[[str, dict[str, Any]], float],
) -> Callable[[str, dict[str, Any]], float]:
    """Обёртка над score_fn: шумные фрагменты получают низкий вес."""

    def score(query: str, chunk: dict[str, Any]) -> float:
        base = base_score_fn(query, chunk)
        if base <= 0:
            return 0.0
        quality = chunk_text_quality(chunk.get("content_preview") or "")
        if quality < 0.12:
            return 0.0
        overlap = keyword_overlap(query, chunk.get("content_preview") or "")
        return base * (0.5 + 0.5 * quality) + 0.2 * overlap

    return score
