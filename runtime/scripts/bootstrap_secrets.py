#!/usr/bin/env python3
"""Собрать secrets.local из переменных окружения (без вывода значений)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
TARGET = RUNTIME / "secrets.local"

KEYS = [
    "OPENAI_API_KEY",
    "MINERU_API_KEY",
    "MISTRAL_API_KEY",
]

DEFAULTS = {
    "TMKI_LLM_PROVIDER": "openai",
    "OPENAI_MODEL": "gpt-4o-mini",
    "TMKI_OCR_MODE": "http",
    "MINERU_API_URL": "https://mineru.net/api/v4",
    "MISTRAL_OCR_API_URL": "https://api.mistral.ai/v1/ocr",
    "MISTRAL_OCR_MODEL": "mistral-ocr-latest",
    "TMKI_ARM_KS_ARCHIVE": r"D:\Курсор\Армировка КС",
    "TMKI_REGULATIONS_ARCHIVE": r"D:\Курсор\СКРУ-2",
}


def _pick(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if val and val not in {"sk-...", "..."}:
        return val
    return ""


def main() -> int:
    found = {k: _pick(k) for k in KEYS}
    missing = [k for k, v in found.items() if not v]
    if missing:
        print("MISSING:" + ",".join(missing), file=sys.stderr)
        return 2

    lines = [
        "# auto bootstrap_secrets.py",
        "",
    ]
    for k, v in DEFAULTS.items():
        lines.append(f"{k}={v}")
    for k, v in found.items():
        lines.append(f"{k}={v}")

    TARGET.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE:{TARGET}")
    print("OK:" + ",".join(KEYS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
