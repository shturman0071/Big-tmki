"""Тесты расширенного ingest: форматы, DWG, DOC, xlsx."""

from __future__ import annotations

import zipfile
from io import BytesIO

import pytest

from tmki_ingest.regulations import CATALOG_ONLY_EXTENSIONS, INGEST_EXTENSIONS, _classify_extension
from tmki_ocr.dwg_extract import extract_dwg_text
from tmki_ocr.extractors import extract_docx, extract_local_text, extract_xlsx


def test_ingest_extensions_include_lab_formats():
    for ext in (".tif", ".xlsx", ".pptx", ".zip", ".dwg", ".csv", ".sdr"):
        assert ext in INGEST_EXTENSIONS
    assert _classify_extension(".dwg") == "ingest_candidate"
    assert _classify_extension(".dxf") == "catalog_only"
    assert _classify_extension(".cdw") == "catalog_only"


def test_extract_xlsx_shared_strings():
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "xl/sharedStrings.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <si><t>Маркшейдерия</t></si>
            </sst>""",
        )
    text = extract_xlsx(buf.getvalue())
    assert "Маркшейдерия" in text


def test_extract_csv():
    raw = "колонка1;колонка2\nзначение;123".encode("utf-8")
    out = extract_local_text(raw, suffix=".csv")
    assert "значение" in out["text"]


def test_extract_dwg_strings():
    raw = b"AC1027\x00" + b"Layer_MARKSHEIDER\x00" + "Схема ствола".encode("cp1251")
    out = extract_dwg_text(raw)
    assert out["text"]
    assert "Layer" in out["text"] or "Схема" in out["text"]


def test_extract_docx_minimal_still_works():
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body><w:p><w:r><w:t>Акт маркшейдерский</w:t></w:r></w:p></w:body>
            </w:document>""",
        )
    assert "Акт" in extract_docx(buf.getvalue())


def test_catalog_only_dxf_not_ingest():
    assert ".dxf" in CATALOG_ONLY_EXTENSIONS
    assert ".dxf" not in INGEST_EXTENSIONS
