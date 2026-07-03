from tmki_rag.lemmatize import lemmatize_word, lemmatize_tokens, lemma_set
from tmki_rag.search import _default_score


def test_lemmatize_cases_to_normal_form():
    if not __import__("tmki_rag.lemmatize", fromlist=["lemmatize_available"]).lemmatize_available():
        import pytest

        pytest.skip("pymorphy3 not installed")
    assert lemmatize_word("договору") == "договор"
    assert lemmatize_word("договоры") == "договор"
    assert lemmatize_word("маркшейдерской") == "маркшейдерский"


def test_lemmatize_tokens_ignores_short():
    tokens = lemmatize_tokens("о на кран ОПО")
    assert "кран" in tokens
    assert "о" not in tokens


def test_default_score_matches_across_cases():
    chunk = {"content_preview": "Требования к маркшейдерской съёмке и договору подряда"}
    score = _default_score("маркшейдерская съемка договор", chunk)
    assert score > 0.5


def test_lemma_set_dedup():
    s = lemma_set("кран краны крану")
    assert len(s) <= 2
