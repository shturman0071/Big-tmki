"""Repair UTF-8 CLI text mangled by Windows PowerShell/cmd argv encoding."""

from __future__ import annotations

import os
import sys


def _cyrillic_count(text: str) -> int:
    return sum(1 for ch in text if "\u0400" <= ch <= "\u04FF")


def fix_windows_cli_text(text: str) -> str:
    """Decode UTF-8 bytes that were mis-read as Latin-1/cp1252 on Windows argv."""
    if not text or sys.platform != "win32":
        return text
    for encoding in ("latin-1", "cp1252"):
        try:
            repaired = text.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if _cyrillic_count(repaired) > _cyrillic_count(text):
            return repaired
    return text


def resolve_cli_message(*, positional: str | None, env_key: str = "TMKI_MVP_MESSAGE", default: str) -> str:
    raw = (positional or "").strip() or os.environ.get(env_key) or default
    return fix_windows_cli_text(raw)


def safe_console_text(text: str) -> str:
    """Сделать строку безопасной для stdout/stderr (cp1251 и др.)."""
    if not text:
        return text
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        text.encode(encoding)
        return text
    except UnicodeEncodeError:
        return text.encode(encoding, errors="backslashreplace").decode(encoding)
