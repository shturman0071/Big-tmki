from __future__ import annotations

from typing import Any


class ChunkIndex:
    """In-memory индекс chunks (MVP до pgvector)."""

    def __init__(self, chunks: list[dict[str, Any]] | None = None) -> None:
        self._chunks: list[dict[str, Any]] = list(chunks or [])

    def add(self, chunks: list[dict[str, Any]]) -> int:
        self._chunks.extend(chunks)
        return len(chunks)

    def list(self) -> list[dict[str, Any]]:
        return list(self._chunks)

    def clear(self) -> None:
        self._chunks.clear()
