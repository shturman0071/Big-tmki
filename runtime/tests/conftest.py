from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_ocr_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """OCR-тесты ожидают stub по умолчанию (не наследовать shell env)."""
    monkeypatch.setenv("TMKI_OCR_MODE", "stub")
