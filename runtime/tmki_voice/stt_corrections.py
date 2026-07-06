"""Пост-обработка STT: типичные ошибки Whisper на доменной лексике TMKI."""

from __future__ import annotations

import re

# Подсказка Whisper — смещает токены к нужной лексике (все пресеты).
DOMAIN_INITIAL_PROMPT = (
    "Голосовой запрос по регламентам и архиву. "
    "Проминвест, Балыко, ТТН, транспортная накладная, документ о качестве, "
    "журнал сварочных работ, журнал входного контроля, акт скрытых работ, "
    "акт освидетельствования, армировка КС, СКРУ-2, промбезопасность, ГОСТ, арматура А500."
)

# (pattern, replacement) — порядок важен: сначала длинные/специфичные.
_PHRASE_FIXES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bром[\s-]*инвест\b", re.I), "Проминвест"),
    (re.compile(r"\bром[аоэ]?н(?:ный\s+въезд|вест|инвест|энвест)\b", re.I), "Проминвест"),
    (re.compile(r"\bпроминвест\s+балык[аоу]?\b", re.I), "Проминвест Балыко"),
    (re.compile(r"\bроминвест\s*\.?\s*балык[аоу]?\b", re.I), "Проминвест Балыко"),
    (re.compile(r"\bбаллыква\b", re.I), "Балыко"),
    (re.compile(r"\bбалыква\b", re.I), "Балыко"),
    (re.compile(r"\bполыко\b", re.I), "Балыко"),
    (re.compile(r"\bволыко\b", re.I), "Балыко"),
    (re.compile(r"\bбалыка\b", re.I), "Балыко"),
    (re.compile(r"\bгурналы\b", re.I), "журналы"),
    (re.compile(r"\bгурнал\b", re.I), "журнал"),
    (re.compile(r"\bнурнал\b", re.I), "журнал"),
    (re.compile(r"\bакт[ау]\s+о\s+свидетельствовании\b", re.I), "акт освидетельствования"),
    (re.compile(r"\bакт[ау]\s+свидетельствования\b", re.I), "акт освидетельствования"),
    (re.compile(r"\bдокументам\s+о\s+качестве\b", re.I), "документу о качестве"),
    (re.compile(r"\bттн\s+у\s+армировки\b", re.I), "ТТН по армировке"),
    (re.compile(r"\bподписанный\s+ттн\s+о\s+армировке\b", re.I), "подписанные ТТН по армировке"),
    (re.compile(r"\bподписанный\s+ттн\s+у\s+армировке\b", re.I), "подписанные ТТН по армировке"),
]

# ТТН часто путают с ДТН/ПТН — только в контексте армировки/накладной.
_TTN_CONTEXT = re.compile(
    r"\b(дтн|птн)\b(?=[\s,.«\"—-]*(?:армировк|накладн|транспортн))",
    re.I,
)
_TTN_STANDALONE = re.compile(
    r"\bнайди\s+(дтн|птн)\b",
    re.I,
)


def _normalize_stt_text(text: str) -> str:
    import unicodedata

    out = unicodedata.normalize("NFKC", text)
    for ch in ("\u00a0", "\u202f", "\u2009"):
        out = out.replace(ch, " ")
    return out.strip()


def apply_stt_corrections(text: str) -> str:
    """Исправляет частые фонетические ошибки STT без изменения остального текста."""
    if not text or not text.strip():
        return text

    out = _normalize_stt_text(text)
    for pattern, repl in _PHRASE_FIXES:
        out = pattern.sub(repl, out)

    out = _TTN_CONTEXT.sub("ТТН", out)
    out = _TTN_STANDALONE.sub(lambda m: m.group(0).replace(m.group(1), "ТТН"), out)

    # «ДТН, армировка» / «ПТН, армировка»
    out = re.sub(r"\b(дтн|птн)\s*[,;]\s*армировк", "ТТН, армировк", out, flags=re.I)

    try:
        from tmki_voice.stt_learn import apply_learned_corrections

        out = apply_learned_corrections(out)
    except ImportError:
        pass

    return re.sub(r"\s+", " ", out).strip()


def stt_fix_selftest() -> dict[str, str]:
    """Проверка, что пост-обработка загружена (для /api/status)."""
    sample = "Роминвест. Балыка."
    fixed = apply_stt_corrections(sample)
    return {
        "sample_in": sample,
        "sample_out": fixed,
        "ok": fixed.startswith("Проминвест") and "Балыко" in fixed,
    }
