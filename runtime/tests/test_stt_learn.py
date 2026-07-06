"""Тесты обучения STT из пользовательских правок."""

from __future__ import annotations

from pathlib import Path

import pytest

from tmki_voice import stt_learn


@pytest.fixture()
def learned_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db = tmp_path / "stt-learned.json"
    monkeypatch.setattr(stt_learn, "LEARNED_DB", db)
    stt_learn._reload_learned_patterns()
    yield db
    stt_learn._reload_learned_patterns()


def test_record_stt_correction_adds_rule(learned_db: Path):
    added = stt_learn.record_stt_correction("ром инвест", "Проминвест", session_id="s1")
    assert added
    assert stt_learn.apply_learned_corrections("ром инвест в архиве") == "Проминвест в архиве"


def test_record_stt_correction_skips_identical(learned_db: Path):
    assert stt_learn.record_stt_correction("текст", "текст") == []


def test_extract_pairs_replace():
    pairs = stt_learn._extract_pairs("балыква в журнале", "Балыко в журнале")
    assert ("балыква", "Балыко") in pairs
