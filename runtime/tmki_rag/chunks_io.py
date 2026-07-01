from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_REGULATIONS_CHUNKS = (
    Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import" / "chunks.json"
)


def load_chunks_file(path: Path) -> list[dict[str, Any]]:
    """Загрузить chunks из JSON (`{"chunks": [...]}`)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    chunks = data.get("chunks", data if isinstance(data, list) else [])
    if not isinstance(chunks, list):
        raise ValueError(f"Неверный формат chunks: {path}")
    return chunks


def load_regulations_chunks(path: Path | None = None) -> list[dict[str, Any]]:
    """Chunks из полного stub-импорта регламентов (локальный artifact)."""
    target = path or DEFAULT_REGULATIONS_CHUNKS
    if not target.is_file():
        raise FileNotFoundError(f"Файл chunks не найден: {target}")
    return load_chunks_file(target)
