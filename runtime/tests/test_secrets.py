from tmki_runtime.secrets import is_placeholder_secret, is_valid_openai_api_key


def test_placeholder_openai_key():
    assert not is_valid_openai_api_key("sk-...")
    assert not is_valid_openai_api_key("")
    assert is_placeholder_secret("sk-...")


def test_real_openai_key_shape():
    assert is_valid_openai_api_key("sk-proj-" + "a" * 24)
