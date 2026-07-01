from __future__ import annotations

_CLEARANCE_RANK = {
    "public": 0,
    "internal": 1,
    "restricted": 2,
    "confidential": 3,
}


def clearance_allows(chunk_classification: str, user_clearance: str) -> bool:
    """chunk.classification <= user.clearance (S_label)."""
    return _CLEARANCE_RANK.get(chunk_classification, 99) <= _CLEARANCE_RANK.get(user_clearance, -1)


def classification_meets_minimum(classification: str, minimum: str) -> bool:
    """Документ MUST быть не менее строгим, чем default_classification папки."""
    return _CLEARANCE_RANK.get(classification, 99) >= _CLEARANCE_RANK.get(minimum, 0)
