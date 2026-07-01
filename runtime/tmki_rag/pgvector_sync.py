from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def sync_state_path(chunks_path: Path) -> Path:
    return chunks_path.parent / "pgvector-sync-state.json"


def load_pgvector_sync_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_pgvector_sync_state(
    path: Path,
    *,
    variant: str,
    chunks_path: Path,
    loaded_count: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "0.1",
        "variant": variant,
        "chunks_path": str(chunks_path),
        "loaded_count": loaded_count,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def slice_chunks_for_incremental(
    chunks: list[dict[str, Any]],
    *,
    variant: str,
    chunks_path: Path,
    state_path: Path,
) -> tuple[list[dict[str, Any]], int]:
    """Вернуть только новые chunks с прошлой incremental-загрузки."""
    state = load_pgvector_sync_state(state_path)
    if state.get("variant") != variant or state.get("chunks_path") != str(chunks_path):
        return chunks, 0
    offset = int(state.get("loaded_count") or 0)
    if offset >= len(chunks):
        return [], offset
    return chunks[offset:], offset
