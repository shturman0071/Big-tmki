"""Тесты пост-обработки STT."""

from __future__ import annotations

from tmki_voice.stt_corrections import apply_stt_corrections


def test_prominvest_balyko():
    assert apply_stt_corrections("Ромэнвест. Балыка.") == "Проминвест. Балыко."
    assert apply_stt_corrections("Романный въезд. Балыко.") == "Проминвест. Балыко."
    assert apply_stt_corrections("Ромэнвест, Волыко.") == "Проминвест, Балыко."
    assert apply_stt_corrections("Роминвест. Балыка.") == "Проминвест. Балыко."
    assert apply_stt_corrections("РОМ-ИНВЕСТ БАЛЫКО") == "Проминвест Балыко"


def test_journal_typos():
    assert apply_stt_corrections("Нурнал сварочных работ.") == "журнал сварочных работ."
    assert apply_stt_corrections("Гурналы входного контроля материалов.") == "журналы входного контроля материалов."


def test_ttn_confusion():
    assert apply_stt_corrections("ДТН, армировка.") == "ТТН, армировка."
    assert apply_stt_corrections("ПТН, армировка.") == "ТТН, армировка."
    assert apply_stt_corrections("Найди ДТН-армировка.") == "Найди ТТН-армировка."


def test_act_and_document():
    assert (
        apply_stt_corrections("Акта о свидетельствовании скрытых работ фундамента.")
        == "акт освидетельствования скрытых работ фундамента."
    )
    assert (
        apply_stt_corrections("Какие замечания к документам о качестве 453?")
        == "Какие замечания к документу о качестве 453?"
    )


def test_ttn_armirovka_phrases():
    assert (
        apply_stt_corrections("Покажи подписанный ТТН у армировки.")
        == "Покажи подписанный ТТН по армировке."
    )
