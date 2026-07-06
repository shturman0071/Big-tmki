from __future__ import annotations

from pathlib import Path
from typing import Any

from tmki_ingest.regulations import CATALOG_ONLY_EXTENSIONS, INGEST_EXTENSIONS
from tmki_ocr.extractors import extract_local_text, guess_suffix

_PREVIEW_CHARS = 400


def read_file(path: Path) -> dict[str, Any]:
    """Прочитать файл: все ingest-форматы через локальный extractor."""
    path = Path(path)
    suffix = path.suffix.lower()
    raw = path.read_bytes()

    if suffix in CATALOG_ONLY_EXTENSIONS:
        return {
            "path": str(path),
            "suffix": suffix,
            "category": "catalog_only",
            "readable": False,
            "method": "catalog_only",
            "preview": "",
            "detail": (
                f"Формат {suffix} — только каталог (метаданные). "
                "Чертежи в RAG: только .dwg; .dxf/.cdw — не индексируются."
            ),
            "confidence": 0.0,
        }

    extracted = extract_local_text(raw, suffix=suffix or guess_suffix(raw, path.name), source_name=path.name)
    category = "ingest" if suffix in INGEST_EXTENSIONS else "generic"

    text = (extracted.get("text") or "").strip()
    preview = text[:_PREVIEW_CHARS]
    if len(text) > _PREVIEW_CHARS:
        preview += "…"

    return {
        "path": str(path),
        "suffix": suffix,
        "category": category,
        "readable": bool(text),
        "method": extracted.get("method"),
        "page_count": extracted.get("page_count"),
        "confidence": extracted.get("confidence"),
        "chars": len(text),
        "preview": preview,
    }


def format_support_matrix() -> list[dict[str, str]]:
    ingest = sorted(INGEST_EXTENSIONS)
    catalog = sorted(CATALOG_ONLY_EXTENSIONS)
    rows: list[dict[str, str]] = []
    for ext in ingest:
        note = "OCR/local → RAG"
        if ext == ".dwg":
            note = "Подписи слоёв/блоков из DWG → RAG"
        elif ext == ".doc":
            note = "LibreOffice .doc→.docx → RAG"
        rows.append({"extension": ext, "status": "read_ingest", "note": note})
    for ext in catalog:
        rows.append({"extension": ext, "status": "catalog_only", "note": "Метаданные в manifest"})
    return rows
