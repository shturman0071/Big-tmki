from __future__ import annotations

import io
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_P_NS = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_XLSX_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_ZIP_INNER_EXTS = frozenset({".txt", ".md", ".csv", ".xml", ".json", ".rtf", ".docx", ".pdf"})


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


def extract_xlsx(raw_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            if "xl/sharedStrings.xml" not in zf.namelist():
                return ""
            xml = zf.read("xl/sharedStrings.xml")
    except zipfile.BadZipFile:
        return ""
    root = ET.fromstring(xml)
    parts: list[str] = []
    for si in root.findall(".//m:si", _XLSX_NS):
        texts = [t.text or "" for t in si.findall(".//m:t", _XLSX_NS)]
        line = "".join(texts).strip()
        if line:
            parts.append(line)
    return "\n".join(parts).strip()


def extract_pptx(raw_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            slide_names = sorted(n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
            parts: list[str] = []
            for name in slide_names:
                root = ET.fromstring(zf.read(name))
                texts = [t.text or "" for t in root.iter(f"{_A_NS}t")]
                line = " ".join(x for x in texts if x).strip()
                if line:
                    parts.append(line)
    except (zipfile.BadZipFile, ET.ParseError):
        return ""
    return "\n".join(parts).strip()


def extract_image_tesseract(raw_bytes: bytes) -> tuple[str, int] | None:
    if os.environ.get("TMKI_LOCAL_TESSERACT", "1").lower() in ("0", "false", "no"):
        return None
    tess = _find_tesseract()
    if not tess:
        return None
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return None
    pytesseract.pytesseract.tesseract_cmd = tess
    prefix = _tessdata_prefix()
    if prefix:
        os.environ["TESSDATA_PREFIX"] = prefix
    lang = os.environ.get("TESSERACT_LANG", "rus+eng" if prefix else "eng")
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        text = pytesseract.image_to_string(img, lang=lang).strip()
    except Exception:
        return None
    return text, 1


def _extract_binary_strings(raw_bytes: bytes, *, min_len: int = 5) -> str:
    parts: list[str] = []
    for m in re.finditer(rb"[\x20-\x7e\xc0-\xff]{%d,}" % min_len, raw_bytes):
        try:
            parts.append(m.group().decode("cp1251", errors="ignore"))
        except Exception:
            parts.append(m.group().decode("latin-1", errors="ignore"))
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return "\n".join(out[:300]).strip()


def extract_zip_text(raw_bytes: bytes) -> str:
    max_files = int(os.environ.get("TMKI_ZIP_MAX_FILES", "25"))
    max_inner = int(os.environ.get("TMKI_ZIP_MAX_BYTES", str(2 * 1024 * 1024)))
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            parts: list[str] = []
            for info in zf.infolist()[:max_files]:
                if info.is_dir() or info.file_size > max_inner:
                    continue
                inner_name = info.filename
                suffix = Path(inner_name).suffix.lower()
                if suffix not in _ZIP_INNER_EXTS:
                    continue
                try:
                    inner = zf.read(info)
                except Exception:
                    continue
                sub = extract_local_text(inner, suffix=suffix)
                text = (sub.get("text") or "").strip()
                if text:
                    parts.append(f"[{inner_name}]\n{text}")
    except zipfile.BadZipFile:
        return ""
    return "\n\n".join(parts).strip()


def extract_doc_with_conversion(raw_bytes: bytes, *, source_name: str | None = None) -> dict[str, Any]:
    from tmki_ocr.doc_convert import convert_doc_to_docx_bytes

    docx_bytes = convert_doc_to_docx_bytes(raw_bytes, source_name=source_name or "document.doc")
    if docx_bytes:
        try:
            text = extract_docx(docx_bytes)
            if text:
                return {
                    "text": text,
                    "page_count": 1,
                    "confidence": 0.9,
                    "method": "doc_libreoffice_docx",
                }
        except (zipfile.BadZipFile, KeyError, ET.ParseError):
            pass
    fallback = _extract_binary_strings(raw_bytes)
    if fallback:
        return {"text": fallback, "page_count": 1, "confidence": 0.35, "method": "doc_strings_fallback"}
    return {"text": "", "page_count": 0, "confidence": 0.0, "method": "doc_convert_failed"}


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


def extract_local_text(raw_bytes: bytes, *, suffix: str, source_name: str | None = None) -> dict[str, Any]:
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
        return extract_doc_with_conversion(raw_bytes, source_name=source_name)

    if ext in {".xlsx", ".xlsm"}:
        text = extract_xlsx(raw_bytes)
        return {"text": text, "page_count": 1, "confidence": 0.85 if len(text) > 20 else 0.3, "method": "xlsx_strings"}

    if ext == ".xls":
        text = _extract_binary_strings(raw_bytes)
        return {"text": text, "page_count": 1, "confidence": 0.4 if text else 0.0, "method": "xls_strings"}

    if ext == ".csv":
        text = _decode_text(raw_bytes).strip()
        return {"text": text, "page_count": 1, "confidence": 0.9 if text else 0.0, "method": "csv"}

    if ext == ".pptx":
        text = extract_pptx(raw_bytes)
        return {"text": text, "page_count": 1, "confidence": 0.85 if len(text) > 20 else 0.3, "method": "pptx_xml"}

    if ext == ".ppt":
        text = _extract_binary_strings(raw_bytes)
        return {"text": text, "page_count": 1, "confidence": 0.35 if text else 0.0, "method": "ppt_strings"}

    if ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif", ".webp", ".bmp"}:
        ocr = extract_image_tesseract(raw_bytes)
        if ocr and ocr[0]:
            return {"text": ocr[0], "page_count": ocr[1], "confidence": 0.8 if len(ocr[0]) > 30 else 0.5, "method": "tesseract_image"}
        return {"text": "", "page_count": 0, "confidence": 0.0, "method": "image_no_tesseract"}

    if ext == ".dwg":
        from tmki_ocr.dwg_extract import extract_dwg_text

        return extract_dwg_text(raw_bytes)

    if ext == ".zip":
        text = extract_zip_text(raw_bytes)
        return {"text": text, "page_count": 1, "confidence": 0.7 if len(text) > 40 else 0.25, "method": "zip_inner"}

    if ext == ".sdr":
        text = _decode_text(raw_bytes).strip() or _extract_binary_strings(raw_bytes)
        return {"text": text, "page_count": 1, "confidence": 0.65 if text else 0.0, "method": "sdr_text"}

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

