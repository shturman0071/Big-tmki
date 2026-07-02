from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

from tmki_ingest.regulations import CATALOG_ONLY_EXTENSIONS, INGEST_EXTENSIONS
from tmki_ocr.extractors import extract_local_text, guess_suffix

_PREVIEW_CHARS = 400


def _extract_xlsx_preview(raw_bytes: bytes) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            if "xl/sharedStrings.xml" not in zf.namelist():
                return {"text": "", "method": "xlsx_no_strings", "confidence": 0.0}
            xml = zf.read("xl/sharedStrings.xml")
    except zipfile.BadZipFile:
        return {"text": "", "method": "xlsx_bad_zip", "confidence": 0.0}

    root = ET.fromstring(xml)
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    parts: list[str] = []
    for si in root.findall(".//m:si", ns):
        texts = [t.text or "" for t in si.findall(".//m:t", ns)]
        line = "".join(texts).strip()
        if line:
            parts.append(line)
    text = "\n".join(parts).strip()
    return {
        "text": text,
        "page_count": 1,
        "confidence": 0.85 if len(text) > 20 else 0.3,
        "method": "xlsx_shared_strings",
    }


def read_file(path: Path) -> dict[str, Any]:
    """Прочитать файл: ingest-форматы + preview для xlsx."""
    path = Path(path)
    suffix = path.suffix.lower()
    raw = path.read_bytes()

    if suffix in {".xlsx", ".xlsm"}:
        extracted = _extract_xlsx_preview(raw)
        category = "spreadsheet_preview"
    elif suffix in CATALOG_ONLY_EXTENSIONS:
        return {
            "path": str(path),
            "suffix": suffix,
            "category": "catalog_only",
            "readable": False,
            "method": "catalog_only",
            "preview": "",
            "detail": (
                f"Формат {suffix} зарегистрирован в архиве (метаданные), "
                "полный текст в RAG — backlog (нужен специализированный парсер)."
            ),
            "confidence": 0.0,
        }
    else:
        extracted = extract_local_text(raw, suffix=suffix or guess_suffix(raw, path.name))
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
        rows.append({"extension": ext, "status": "read_ingest", "note": "OCR/local → RAG"})
    rows.append({"extension": ".xlsx", "status": "read_preview", "note": "Текст из sharedStrings (demo)"})
    for ext in catalog:
        if ext == ".xlsx":
            continue
        rows.append({"extension": ext, "status": "catalog_only", "note": "Метаданные в manifest"})
    return rows
