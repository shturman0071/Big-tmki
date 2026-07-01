from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


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
    """MVP chunking: один chunk на OCR результат."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    doc_id = ocr_result["doc_id"]
    preview = markdown[:500]
    chunk: dict[str, Any] = {
        "schema_version": "0.1",
        "chunk_id": f"chunk_{doc_id}_01",
        "doc_id": doc_id,
        "company_id": company_id,
        "project_id": project_id,
        "classification": classification,
        "language": "ru",
        "page": 1,
        "start_offset": 0,
        "end_offset": len(markdown),
        "embedding_model": "text-embedding-3-small",
        "content_preview": preview,
        "indexed_at": now,
    }
    if department_id:
        chunk["department_id"] = department_id
    if folder_id:
        chunk["folder_id"] = folder_id
    return [chunk]
