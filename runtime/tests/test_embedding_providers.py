import pytest

from tmki_rag.embedding_providers import (
    LocalHashEmbeddingProvider,
    OllamaEmbeddingProvider,
    OpenAiEmbeddingProvider,
    get_embedding_provider,
)


def test_local_embedding_provider():
    p = LocalHashEmbeddingProvider(dims=32)
    result = p.embed("маркшейдерская съёмка")
    assert result.provider == "local"
    assert len(result.vector) == 32
    assert result.dimensions == 32


def test_get_embedding_provider_default_local(monkeypatch):
    monkeypatch.delenv("TMKI_EMBEDDING_PROVIDER", raising=False)
    provider = get_embedding_provider()
    assert isinstance(provider, LocalHashEmbeddingProvider)


def test_get_embedding_provider_ollama(monkeypatch):
    monkeypatch.setenv("TMKI_EMBEDDING_PROVIDER", "ollama")
    provider = get_embedding_provider()
    assert isinstance(provider, OllamaEmbeddingProvider)


def test_get_embedding_provider_openai_requires_key(monkeypatch):
    monkeypatch.setenv("TMKI_EMBEDDING_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_embedding_provider()


def test_ollama_embedding_http_mock():
    def mock_urlopen(req, timeout=60):
        class Resp:
            def read(self):
                return b'{"embedding": [0.1, 0.2, 0.3]}'

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        return Resp()

    import urllib.request

    orig = urllib.request.urlopen
    urllib.request.urlopen = mock_urlopen  # type: ignore[assignment]
    try:
        provider = OllamaEmbeddingProvider(base_url="http://ollama.test", model="nomic-embed-text")
        result = provider.embed("test query")
        assert result.provider == "ollama"
        assert result.dimensions == 3
    finally:
        urllib.request.urlopen = orig  # type: ignore[assignment]
