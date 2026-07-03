#!/usr/bin/env python3
"""Проверка secrets.local без вывода значений ключей."""

from __future__ import annotations

import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from tmki_runtime.secrets import is_placeholder_secret, is_valid_openai_api_key

SECRETS = RUNTIME / "secrets.local"


def main() -> int:
    print(f"file_exists: {SECRETS.is_file()}")
    if not SECRETS.is_file():
        print("action: copy secrets.local.example -> secrets.local and add OPENAI_API_KEY")
        return 2

    issues: list[str] = []
    key_line: int | None = None
    for i, line in enumerate(SECRETS.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped.startswith("OPENAI_API_KEY"):
            continue
        key_line = i
        if stripped.startswith("#"):
            issues.append(f"line {i}: OPENAI_API_KEY is commented out")
            continue
        if "=" not in stripped:
            issues.append(f"line {i}: missing '='")
            continue
        _, value = stripped.split("=", 1)
        if "#" in value:
            issues.append(f"line {i}: remove inline comment after the key value")
            value = value.split("#", 1)[0]
        value = value.strip().strip('"').strip("'")
        print(f"line_number: {i}")
        print(f"key_length: {len(value)}")
        print(f"starts_with_sk: {value.startswith('sk-')}")
        print(f"is_placeholder: {is_placeholder_secret(value)}")
        print(f"is_valid: {is_valid_openai_api_key(value)}")

    if key_line is None:
        issues.append("OPENAI_API_KEY line not found — add: OPENAI_API_KEY=sk-...")

    if issues:
        print("issues:")
        for item in issues:
            print(f" - {item}")
        return 1

    if not is_valid_openai_api_key(_read_openai_key()):
        print("action: replace sk-... placeholder with a real key from platform.openai.com")
        return 1

    print("status: ok")
    return 0


def _read_openai_key() -> str:
    for line in SECRETS.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("OPENAI_API_KEY=") and not stripped.startswith("#"):
            return stripped.split("=", 1)[1].strip().strip('"').strip("'").split("#", 1)[0].strip()
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
