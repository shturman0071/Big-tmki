"""Обучение пост-обработки STT из пользовательских правок (голосовой стенд)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parents[1]
LEARNED_DB = RUNTIME / "artifacts" / "demo" / "stt-learned.json"

_MIN_LEN = 2
_MAX_RULES = 500


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_db() -> dict[str, Any]:
    if not LEARNED_DB.is_file():
        return {"rules": [], "events": []}
    try:
        data = json.loads(LEARNED_DB.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"rules": [], "events": []}
    data.setdefault("rules", [])
    data.setdefault("events", [])
    return data


def _save_db(data: dict[str, Any]) -> None:
    LEARNED_DB.parent.mkdir(parents=True, exist_ok=True)
    LEARNED_DB.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _pattern_from_wrong(wrong: str) -> str:
    parts = [re.escape(p) for p in wrong.strip().split() if p]
    if not parts:
        return ""
    if len(parts) == 1:
        core = parts[0]
        return rf"\b{core}\b"
    return r"\s+".join(parts)


def _extract_pairs(raw: str, corrected: str) -> list[tuple[str, str]]:
    raw = raw.strip()
    corrected = corrected.strip()
    if not raw or not corrected or raw == corrected:
        return []

    raw_words = raw.split()
    cor_words = corrected.split()
    sm = SequenceMatcher(None, raw_words, cor_words)
    pairs: list[tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "replace":
            continue
        wrong = " ".join(raw_words[i1:i2]).strip()
        right = " ".join(cor_words[j1:j2]).strip()
        if len(right) < _MIN_LEN:
            continue
        if wrong.lower() == right.lower():
            continue
        if wrong:
            pairs.append((wrong, right))
    return pairs


def record_stt_correction(
    raw_text: str,
    corrected_text: str,
    *,
    session_id: str | None = None,
    corpus_id: str | None = None,
    source: str = "voice-doc",
) -> list[dict[str, str]]:
    """Сохранить правки STT и обновить правила замены."""
    raw_text = (raw_text or "").strip()
    corrected_text = (corrected_text or "").strip()
    if not raw_text or not corrected_text or raw_text == corrected_text:
        return []

    pairs = _extract_pairs(raw_text, corrected_text)
    if not pairs:
        return []

    data = _load_db()
    rules: list[dict[str, Any]] = data["rules"]
    added: list[dict[str, str]] = []

    for wrong, right in pairs:
        pattern = _pattern_from_wrong(wrong)
        if not pattern:
            continue
        existing = next(
            (r for r in rules if r.get("replacement") == right and r.get("wrong") == wrong),
            None,
        )
        if existing:
            existing["count"] = int(existing.get("count") or 0) + 1
            existing["updated_at"] = _now()
        else:
            rules.append(
                {
                    "wrong": wrong,
                    "replacement": right,
                    "pattern": pattern,
                    "source": source,
                    "count": 1,
                    "added_at": _now(),
                    "updated_at": _now(),
                }
            )
            added.append({"wrong": wrong, "replacement": right})

    if len(rules) > _MAX_RULES:
        rules.sort(key=lambda r: int(r.get("count") or 0), reverse=True)
        data["rules"] = rules[:_MAX_RULES]

    events = data.setdefault("events", [])
    events.append(
        {
            "at": _now(),
            "session_id": session_id,
            "corpus_id": corpus_id,
            "raw_text": raw_text,
            "corrected_text": corrected_text,
            "pairs": [{"wrong": w, "replacement": r} for w, r in pairs],
        }
    )
    if len(events) > 2000:
        data["events"] = events[-2000:]

    _save_db(data)
    _reload_learned_patterns()
    return added


_learned_patterns: list[tuple[re.Pattern[str], str]] | None = None


def _reload_learned_patterns() -> None:
    global _learned_patterns
    _learned_patterns = None
    learned_patterns()


def learned_patterns() -> list[tuple[re.Pattern[str], str]]:
    global _learned_patterns
    if _learned_patterns is not None:
        return _learned_patterns

    rules = _load_db().get("rules") or []
    compiled: list[tuple[re.Pattern[str], str]] = []
    for rule in sorted(rules, key=lambda r: len(r.get("wrong") or ""), reverse=True):
        pattern = (rule.get("pattern") or "").strip()
        repl = (rule.get("replacement") or "").strip()
        if not pattern or not repl:
            continue
        try:
            compiled.append((re.compile(pattern, re.I), repl))
        except re.error:
            continue
    _learned_patterns = compiled
    return compiled


def apply_learned_corrections(text: str) -> str:
    if not text or not text.strip():
        return text
    out = text
    for pattern, repl in learned_patterns():
        out = pattern.sub(repl, out)
    return re.sub(r"\s+", " ", out).strip()


def list_learned_rules(limit: int = 50) -> dict[str, Any]:
    data = _load_db()
    rules = sorted(data.get("rules") or [], key=lambda r: int(r.get("count") or 0), reverse=True)
    return {"total": len(rules), "rules": rules[:limit]}
