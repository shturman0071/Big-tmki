from tmki_rag.match_score import filename_contains_doc_number, text_match_score


def test_exact_phrase_beats_case_insensitive():
    assert text_match_score("ОПО", "требования ОПО на участке") == 1.0
    assert text_match_score("опо", "требования ОПО на участке") == 0.93


def test_exact_words_beat_lemma():
    text = "Требования к маркшейдерской съёмке"
    exact = text_match_score("маркшейдерской", text)
    lemma = text_match_score("маркшейдерская", text)
    assert exact > lemma


def test_lemma_when_no_literal():
    text = "договору подряда"
    assert text_match_score("договор", text) > 0.3


def test_kmd_fence_mark_query():
    text = "штампе132Ограждение Ог-1/1.Отсутствует поз.5 на чертеже"
    assert text_match_score("замечания ограждение 1", text) == 1.0
    noise = "5211Ограждение Ог-10/Замечаний нет (+ общие замечания п.1.1, 1.2)"
    assert text_match_score("замечания ограждение 1", noise) < 0.9


def test_multi_word_requires_all_tokens():
    both = "ООО Проминвест, ответственный Балыко, поставка армировки"
    only_one = "договор с Проминвест на поставку"
    assert text_match_score("проминвест балыко", both) >= 0.80
    assert text_match_score("проминвест балыко", only_one) <= 0.52


def test_filename_doc_number_boundary():
    assert filename_contains_doc_number("Документ о качестве №452.pdf", "452")
    assert filename_contains_doc_number("Письмо № 274 от 14.06.2022.pdf", "274")
    assert not filename_contains_doc_number("Документ о качестве № 43.PDF", "452")
    assert not filename_contains_doc_number("Письмо №6 (№14).pdf", "274")
