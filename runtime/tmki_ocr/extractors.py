from __future__ import annotations

import io
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _decode_text(raw_bytes: bytes) -> str:
    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            return raw_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def _strip_rtf(text: str) -> str:
    text = re.sub(r"\\[a-z]+-?\d*\s?", " ", text)
    text = re.sub(r"[{}]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_docx(raw_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    parts: list[str] = []
    for node in root.iter(f"{_W_NS}t"):
        if node.text:
            parts.append(node.text)
        if node.tail:
            parts.append(node.tail)
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _pdf_max_pages() -> int:
    raw = os.environ.get("TMKI_PDF_MAX_PAGES", "300")
    try:
        return max(1, int(raw))
    except ValueError:
        return 300


def _find_tesseract() -> str | None:
    import shutil

    found = shutil.which("tesseract")
    if found:
        return found
    for candidate in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ):
        if Path(candidate).is_file():
            return candidate
    return None


def _tessdata_prefix() -> str | None:
    """Проектный tessdata (rus+eng) если скачан в runtime/tessdata."""
    custom = os.environ.get("TESSDATA_PREFIX", "").strip()
    if custom and Path(custom).is_dir():
        return custom
    project = Path(__file__).resolve().parents[1] / "tessdata"
    if (project / "rus.traineddata").is_file():
        return str(project)
    return None


def extract_pdf_tesseract(raw_bytes: bytes, *, max_pages: int | None = None) -> tuple[str, int] | None:
    """OCR сканов PDF через Tesseract (офлайн, русский)."""
    if os.environ.get("TMKI_LOCAL_TESSERACT", "1").lower() in ("0", "false", "no"):
        return None
    tess = _find_tesseract()
    if not tess:
        return None
    try:
        import fitz  # pymupdf
        import pytesseract
    except ImportError:
        return None

    pytesseract.pytesseract.tesseract_cmd = tess
    prefix = _tessdata_prefix()
    if prefix:
        os.environ["TESSDATA_PREFIX"] = prefix
    lang = os.environ.get("TESSERACT_LANG", "rus+eng" if prefix else "eng")
    limit = max_pages if max_pages is not None else _pdf_max_pages()
    doc = fitz.open(stream=raw_bytes, filetype="pdf")
    pages: list[str] = []
    total = min(len(doc), limit)
    for i in range(total):
        pix = doc.load_page(i).get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        img_bytes = pix.tobytes("png")
        try:
            from PIL import Image

            pages.append(
                pytesseract.image_to_string(Image.open(io.BytesIO(img_bytes)), lang=lang).strip()
            )
        except Exception:
            pages.append("")
    doc.close()
    text = "\n".join(p for p in pages if p).strip()
    return text, total


def extract_pdf(raw_bytes: bytes, *, max_pages: int | None = None) -> tuple[str, int] | None:
    limit = max_pages if max_pages is not None else _pdf_max_pages()
    try:
        import logging

        logging.getLogger("pypdf").setLevel(logging.ERROR)
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        reader = PdfReader(io.BytesIO(raw_bytes), strict=False)
    except Exception:
        return None
    pages: list[str] = []
    total = len(reader.pages)
    for i, page in enumerate(reader.pages):
        if i >= limit:
            break
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    text = "\n".join(pages).strip()
    return text, min(total, limit)


def extract_local_text(raw_bytes: bytes, *, suffix: str) -> dict[str, Any]:
    """
    Локальное извлечение текста без внешнего OCR API.
    Возвращает: text, page_count, confidence, method.
    """
    ext = suffix.lower()
    if ext in {".txt", ".md"}:
        text = _decode_text(raw_bytes).strip()
        return {"text": text, "page_count": 1, "confidence": 0.98 if text else 0.0, "method": "plain_text"}

    if ext == ".rtf":
        text = _strip_rtf(_decode_text(raw_bytes))
        return {"text": text, "page_count": 1, "confidence": 0.9 if len(text) > 20 else 0.3, "method": "rtf_strip"}

    if ext == ".docx":
        try:
            text = extract_docx(raw_bytes)
            return {"text": text, "page_count": 1, "confidence": 0.95 if len(text) > 30 else 0.4, "method": "docx_xml"}
        except (zipfile.BadZipFile, KeyError, ET.ParseError):
            return {"text": "", "page_count": 0, "confidence": 0.0, "method": "docx_xml"}

    if ext == ".pdf":
        pdf = extract_pdf(raw_bytes)
        if pdf is None:
            return {"text": "", "page_count": 0, "confidence": 0.0, "method": "pdf_missing_pypdf"}
        text, pages = pdf
        if len(text) < 20 and pages > 0:
            ocr = extract_pdf_tesseract(raw_bytes, max_pages=pages)
            if ocr and ocr[0]:
                text, pages = ocr
                conf = 0.82 if len(text) > 50 else 0.55
                return {"text": text, "page_count": pages, "confidence": conf, "method": "tesseract"}
        conf = 0.93 if len(text) > 50 else 0.35
        return {"text": text, "page_count": pages, "confidence": conf, "method": "pypdf"}

    if ext == ".doc":
        return {"text": "", "page_count": 0, "confidence": 0.0, "method": "doc_unsupported"}

    text = _decode_text(raw_bytes).strip()
    if text:
        return {"text": text, "page_count": 1, "confidence": 0.7, "method": "binary_decode"}
    return {"text": "", "page_count": 0, "confidence": 0.0, "method": "unknown"}


def guess_suffix(raw_bytes: bytes, source_name: str | None = None) -> str:
    if source_name:
        return Path(source_name).suffix.lower()
    if raw_bytes.startswith(b"%PDF"):
        return ".pdf"
    if raw_bytes.startswith(b"PK\x03\x04"):
        return ".docx"
    if raw_bytes.startswith(b"{\\rtf"):
        return ".rtf"
    return ""

