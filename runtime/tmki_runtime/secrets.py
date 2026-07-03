from __future__ import annotations

import re

_PLACEHOLDER_EXACT = frozenset({"", "...", "sk-...", "sk-your-key", "your-api-key"})
_OPENAI_KEY = re.compile(r"^sk-[A-Za-z0-9_-]{20,}$")


def is_placeholder_secret(value: str | None) -> bool:
    if not value:
        return True
    v = value.strip()
    if v in _PLACEHOLDER_EXACT:
        return True
    if v.endswith("...") and len(v) < 24:
        return True
    return False


def is_valid_openai_api_key(value: str | None) -> bool:
    if is_placeholder_secret(value):
        return False
    return bool(_OPENAI_KEY.match(value.strip()))


def is_valid_api_secret(value: str | None, *, min_len: int = 16) -> bool:
    if is_placeholder_secret(value):
        return False
    return len(value.strip()) >= min_len
