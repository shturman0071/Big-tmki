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

    def remove_by_source_path(self, relative_path: str) -> int:
        """Удалить chunks файла перед повторным incremental ingest."""
        norm = relative_path.replace("\\", "/")
        kept = [
            c
            for c in self._chunks
            if str(c.get("source_relative_path") or "").replace("\\", "/") != norm
        ]
        removed = len(self._chunks) - len(kept)
        self._chunks = kept
        return removed

    def clear(self) -> None:
        self._chunks.clear()
