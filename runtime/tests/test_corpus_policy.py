from unittest.mock import patch

from tmki_rag.corpus_policy import (
    detect_corpus_from_path,
    enforce_llm_for_corpus,
    enforce_llm_for_paths,
    normalize_corpus_id,
)


def test_normalize_corpus_aliases():
    assert normalize_corpus_id("Армировка КС") == "arm-ks"
    assert normalize_corpus_id("skru-2") == "skru-2"


def test_skru2_blocks_openai():
    provider, note = enforce_llm_for_corpus("openai", "skru-2")
    assert provider in ("stub", "ollama")
    assert note and "СКРУ-2" in note


def test_arm_ks_prefers_openai_with_key():
    valid_key = "sk-" + "a" * 48
    with patch.dict("os.environ", {"OPENAI_API_KEY": valid_key, "TMKI_LLM_PROVIDER": "openai"}, clear=False):
        provider, note = enforce_llm_for_corpus("stub", "arm-ks")
    assert provider == "openai"
    assert note and "Армировка КС" in note


def test_arm_ks_uses_ollama_when_openai_deferred():
    valid_key = "sk-" + "a" * 48
    with patch.dict(
        "os.environ",
        {"OPENAI_API_KEY": valid_key, "TMKI_LLM_PROVIDER": "ollama"},
        clear=False,
    ):
        with patch("tmki_rag.corpus_policy._ollama_ready", return_value=True):
            provider, note = enforce_llm_for_corpus("stub", "arm-ks")
    assert provider == "ollama"
    assert note and "отложен" in note.lower()


def test_paths_block_cloud_for_skru2():
    skru = r"D:\Курсор\СКРУ-2\регламент.pdf"
    provider, note = enforce_llm_for_paths("openai", [skru])
    assert provider in ("stub", "ollama")
    assert note and "СКРУ-2" in note


def test_detect_corpus_from_path():
    assert detect_corpus_from_path(r"D:\Курсор\Армировка КС\чертеж.pdf") == "arm-ks"
