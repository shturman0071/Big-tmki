import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from tmki_ocr.extractors import extract_docx, extract_local_text
from tmki_ocr.ocr import LocalMinerUProvider, run_ocr


def test_extract_local_txt():
    raw = "Регламент промбезопасности крана на участке".encode("utf-8")
    result = extract_local_text(raw, suffix=".txt")
    assert "промбезопасности" in result["text"]
    assert result["confidence"] > 0.9


def test_extract_local_docx_minimal():
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body><w:p><w:r><w:t>Маркшейдерская съёмка участка</w:t></w:r></w:p></w:body>
            </w:document>""",
        )
    text = extract_docx(buf.getvalue())
    assert "Маркшейдерская" in text


def test_extract_pdf_respects_max_pages():
    from tmki_ocr.extractors import extract_pdf

    # minimal invalid PDF bytes — should not raise
    result = extract_pdf(b"%PDF-1.4\n", max_pages=1)
    assert result is None or isinstance(result[0], str)


def test_local_ocr_mode(monkeypatch):
    monkeypatch.setenv("TMKI_OCR_MODE", "local")
    raw = "Инструкция по эксплуатации крана".encode("utf-8")
    result = run_ocr(
        doc_id="doc_local",
        trace_id="00000000-0000-4000-8000-000000000080",
        raw_bytes=raw,
        source_name="instrukciya.txt",
    )
    assert result["ocr_status"] == "completed"
    assert "крана" in result["_markdown"]
    assert result["provider_used"] == "mineru"


def test_reindex_regulations_sample(tmp_path, monkeypatch):
    monkeypatch.setenv("TMKI_OCR_MODE", "local")
    from datetime import date

    from tmki_ingest import reindex_regulations_full
    from tmki_policy import build_policy_context, load_org_snapshot
    from tmki_rag import FolderAclContext, load_folder_catalog, load_folder_grants

    root = Path(__file__).resolve().parents[2]
    (tmp_path / "sample.txt").write_text("промбезопасность ОПО кран", encoding="utf-8")
    out = tmp_path / "out"

    snapshot = load_org_snapshot(root / "schemas/org/examples/satimol-snapshot.example.json")
    ctx = build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )
    acl = FolderAclContext.from_catalog(
        load_folder_catalog(root / "schemas/document/examples/satimol-folders.example.json"),
        load_folder_grants(root / "schemas/org/examples/satimol-folder-grants.example.json"),
        as_of=date(2025, 9, 10),
    )

    result = reindex_regulations_full(
        tmp_path,
        policy_context=ctx,
        classification="restricted",
        folder_id="folder_ms_open",
        folder_acl=acl,
        output_dir=out,
        resume=False,
    )
    assert result["imported_count"] == 1
    chunks = __import__("json").loads((out / "chunks-v2.json").read_text(encoding="utf-8"))["chunks"]
    assert "промбезопасность" in chunks[0]["content_preview"]
