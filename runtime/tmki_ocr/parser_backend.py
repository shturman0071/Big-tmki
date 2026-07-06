"""Маршрутизация ingest-парсеров: default / docling / kreuzberg (отложенные)."""

from __future__ import annotations

import os
from typing import Any

from tmki_ocr.extractors import extract_local_text


def resolve_parser_backend() -> str:
    return os.environ.get("TMKI_INGEST_PARSER", "default").lower().strip() or "default"


def _try_docling(raw_bytes: bytes, *, suffix: str) -> dict[str, Any] | None:
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        return None
    import tempfile
    from pathlib import Path

    ext = suffix if suffix.startswith(".") else f".{suffix}"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = Path(tmp.name)
    try:
        result = DocumentConverter().convert(str(tmp_path))
        text = result.document.export_to_markdown() or ""
        pages = len(getattr(result.document, "pages", []) or []) or 1
        return {
            "text": text.strip(),
            "page_count": pages,
            "confidence": 0.9 if len(text) > 50 else 0.4,
            "method": "docling",
        }
    except Exception:
        return None
    finally:
        tmp_path.unlink(missing_ok=True)


def _try_kreuzberg(raw_bytes: bytes, *, suffix: str) -> dict[str, Any] | None:
    for mod_name in ("kreuzberg", "xberg"):
        try:
            import importlib

            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        extract_fn = getattr(mod, "extract", None) or getattr(mod, "extract_file", None)
        if extract_fn is None:
            continue
        import tempfile
        from pathlib import Path

        ext = suffix if suffix.startswith(".") else f".{suffix}"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = Path(tmp.name)
        try:
            result = extract_fn(str(tmp_path))
            if isinstance(result, dict):
                text = result.get("text") or result.get("content") or ""
            else:
                text = getattr(result, "text", None) or str(result)
            return {
                "text": str(text).strip(),
                "page_count": int(result.get("page_count", 1) if isinstance(result, dict) else 1),
                "confidence": 0.88 if len(str(text)) > 50 else 0.4,
                "method": mod_name,
            }
        except Exception:
            return None
        finally:
            tmp_path.unlink(missing_ok=True)
    return None


def extract_document(raw_bytes: bytes, *, suffix: str, source_name: str | None = None) -> dict[str, Any]:
    """
    TMKI_INGEST_PARSER:
      default — pypdf/tesseract/docx (tmki_ocr.extractors)
      docling — IBM Docling (pip install docling), fallback default
      kreuzberg|xberg — Kreuzberg/Xberg (pip install kreuzberg), fallback default
    """
    backend = resolve_parser_backend()
    if backend == "docling":
        parsed = _try_docling(raw_bytes, suffix=suffix)
        if parsed and parsed.get("text"):
            return parsed
    elif backend in ("kreuzberg", "xberg"):
        parsed = _try_kreuzberg(raw_bytes, suffix=suffix)
        if parsed and parsed.get("text"):
            return parsed
    return extract_local_text(raw_bytes, suffix=suffix, source_name=source_name)
