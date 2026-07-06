"""Извлечение текста из DWG (чертежи — только .dwg)."""

from __future__ import annotations

import re
from typing import Any


_ASCII_RUN = re.compile(rb"[\x20-\x7e\xc0-\xff]{4,}")
_UTF16_RUN = re.compile(rb"(?:[\x20-\x7e]\x00){4,}")


def _unique_lines(parts: list[str], *, limit: int = 400) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for raw in parts:
        line = " ".join(raw.split())
        if len(line) < 3:
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
        if len(out) >= limit:
            break
    return "\n".join(out)


def extract_dwg_text(raw_bytes: bytes) -> dict[str, Any]:
    """
    Текстовые подписи из DWG: слои, блоки, атрибуты (ASCII/UTF-16 в бинарнике).
    Полноценный разбор геометрии — через ODA/dxf (backlog); для RAG достаточно подписей.
    """
    if not raw_bytes.startswith(b"AC10"):
        # не заголовок AutoCAD DWG — всё равно попробуем строки
        method = "dwg_strings"
    else:
        method = "dwg_strings"

    parts: list[str] = []
    for m in _ASCII_RUN.finditer(raw_bytes):
        try:
            parts.append(m.group().decode("cp1251", errors="ignore"))
        except Exception:
            parts.append(m.group().decode("latin-1", errors="ignore"))
    for m in _UTF16_RUN.finditer(raw_bytes):
        try:
            parts.append(m.group().decode("utf-16-le", errors="ignore"))
        except Exception:
            continue

    text = _unique_lines(parts)
    conf = 0.75 if len(text) > 80 else (0.45 if text else 0.0)
    return {
        "text": text,
        "page_count": 1,
        "confidence": conf,
        "method": method,
    }
