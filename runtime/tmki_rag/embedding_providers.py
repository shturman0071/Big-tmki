from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from tmki_rag.embeddings import text_embedding


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]
    provider: str
    model: str
    dimensions: int


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> EmbeddingResult: ...


class LocalHashEmbeddingProvider:
    """Детерминированный local hash embedding (default, без сети)."""

    def __init__(self, *, dims: int = 64, model: str = "local-hash-v1") -> None:
        self._dims = dims
        self._model = model

    def embed(self, text: str) -> EmbeddingResult:
        vec = text_embedding(text, dims=self._dims)
        return EmbeddingResult(
            vector=vec,
            provider="local",
            model=self._model,
            dimensions=self._dims,
        )


class OpenAiEmbeddingProvider:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str | None = None,
        base_url: str = "https://api.openai.com/v1/embeddings",
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model or os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self._base_url = base_url

    def embed(self, text: str) -> EmbeddingResult:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY не задан для TMKI_EMBEDDING_PROVIDER=openai")
        payload = {"model": self._model, "input": text}
        req = urllib.request.Request(
            self._base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI embeddings {exc.code}: {body}") from exc
        vec = data["data"][0]["embedding"]
        return EmbeddingResult(
            vector=vec,
            provider="openai",
            model=self._model,
            dimensions=len(vec),
        )


class OllamaEmbeddingProvider:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._base_url = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self._model = model or os.environ.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

    def embed(self, text: str) -> EmbeddingResult:
        payload = {"model": self._model, "prompt": text}
        req = urllib.request.Request(
            f"{self._base_url}/api/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama embeddings {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama недоступен ({self._base_url}): {exc.reason}") from exc
        vec = data.get("embedding") or []
        return EmbeddingResult(
            vector=vec,
            provider="ollama",
            model=self._model,
            dimensions=len(vec),
        )


def get_embedding_provider() -> EmbeddingProvider:
    """
    TMKI_EMBEDDING_PROVIDER=local|openai|ollama (default local).
    TMKI_EMBEDDING_DIMS — для local provider (default 64).
    """
    name = os.environ.get("TMKI_EMBEDDING_PROVIDER", "local").lower()
    dims = int(os.environ.get("TMKI_EMBEDDING_DIMS", "64"))
    if name == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY не задан для TMKI_EMBEDDING_PROVIDER=openai")
        return OpenAiEmbeddingProvider(key)
    if name == "ollama":
        return OllamaEmbeddingProvider()
    return LocalHashEmbeddingProvider(dims=dims)
