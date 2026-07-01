from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

DEFAULT_REGULATIONS_CHUNKS = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "chunks.json"
)
DEFAULT_REGULATIONS_CHUNKS_V2 = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "chunks-v2.json"
)

ChunksVariant = Literal["v1", "v2", "auto"]


def load_chunks_file(path: Path) -> list[dict[str, Any]]:
    """Загрузить chunks из JSON (`{"chunks": [...]}`)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    chunks = data.get("chunks", data if isinstance(data, list) else [])
    if not isinstance(chunks, list):
        raise ValueError(f"Неверный формат chunks: {path}")
    return chunks


def resolve_regulations_chunks_path(variant: ChunksVariant = "auto") -> Path:
    """v2 (local OCR) если есть, иначе v1 (stub)."""
    if variant == "v2":
        if not DEFAULT_REGULATIONS_CHUNKS_V2.is_file():
            raise FileNotFoundError(f"chunks-v2 не найден: {DEFAULT_REGULATIONS_CHUNKS_V2}")
        return DEFAULT_REGULATIONS_CHUNKS_V2
    if variant == "v1":
        if not DEFAULT_REGULATIONS_CHUNKS.is_file():
            raise FileNotFoundError(f"chunks не найден: {DEFAULT_REGULATIONS_CHUNKS}")
        return DEFAULT_REGULATIONS_CHUNKS
    if DEFAULT_REGULATIONS_CHUNKS_V2.is_file():
        return DEFAULT_REGULATIONS_CHUNKS_V2
    return DEFAULT_REGULATIONS_CHUNKS


def load_regulations_chunks(
    path: Path | None = None,
    *,
    variant: ChunksVariant = "auto",
) -> list[dict[str, Any]]:
    """Chunks регламентов: auto → chunks-v2.json, иначе chunks.json."""
    target = path or resolve_regulations_chunks_path(variant)
    if not target.is_file():
        raise FileNotFoundError(f"Файл chunks не найден: {target}")
    return load_chunks_file(target)
