from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any


def _chunk_size() -> int:
    return int(os.environ.get("TMKI_CHUNK_SIZE", "1200"))


def _chunk_overlap() -> int:
    return int(os.environ.get("TMKI_CHUNK_OVERLAP", "200"))


def split_text_windows(text: str, *, chunk_size: int | None = None, overlap: int | None = None) -> list[tuple[int, int, str]]:
    """Разбить текст на перекрывающиеся окна для полнотекстового поиска."""
    body = (text or "").strip()
    if not body:
        return []
    size = chunk_size or _chunk_size()
    step = max(1, size - (overlap or _chunk_overlap()))
    if len(body) <= size:
        return [(0, len(body), body)]
    windows: list[tuple[int, int, str]] = []
    start = 0
    while start < len(body):
        end = min(len(body), start + size)
        windows.append((start, end, body[start:end]))
        if end >= len(body):
            break
        start += step
    return windows


def build_chunks_from_ocr(
    ocr_result: dict[str, Any],
    *,
    company_id: str,
    project_id: str,
    department_id: str | None,
    folder_id: str | None,
    classification: str,
    markdown: str,
) -> list[dict[str, Any]]:
    """Chunking: несколько перекрывающихся фрагментов на документ (полный текст в индексе)."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    doc_id = ocr_result["doc_id"]
    windows = split_text_windows(markdown)
    if not windows:
        return []
    chunks: list[dict[str, Any]] = []
    for idx, (start, end, preview) in enumerate(windows, start=1):
        chunk: dict[str, Any] = {
            "schema_version": "0.1",
            "chunk_id": f"chunk_{doc_id}_{idx:02d}",
            "doc_id": doc_id,
            "company_id": company_id,
            "project_id": project_id,
            "classification": classification,
            "language": "ru",
            "page": idx,
            "start_offset": start,
            "end_offset": end,
            "embedding_model": "text-embedding-3-small",
            "content_preview": preview,
            "indexed_at": now,
        }
        if department_id:
            chunk["department_id"] = department_id
        if folder_id:
            chunk["folder_id"] = folder_id
        chunks.append(chunk)
    return chunks
