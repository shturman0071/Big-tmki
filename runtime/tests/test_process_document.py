import base64
from datetime import date
from pathlib import Path

from tmki_ingest import DedupStore, process_document
from tmki_rag import FolderAclContext, load_folder_catalog, load_folder_grants

ROOT = Path(__file__).resolve().parents[2]


def _folder_acl():
    return FolderAclContext.from_catalog(
        load_folder_catalog(ROOT / "schemas/document/examples/satimol-folders.example.json"),
        load_folder_grants(ROOT / "schemas/org/examples/satimol-folder-grants.example.json"),
        as_of=date(2025, 9, 10),
    )


def _request(raw: bytes):
    return {
        "schema_version": "0.1",
        "trace_id": "00000000-0000-4000-8000-000000000010",
        "policy_context": {
            "company_id": "company_tmki_ru",
            "project_id": "project_satimol",
            "department_id": "dept_markscheider",
            "project_role": "Сотрудник подразделения",
            "employee_id": "emp_staff_x",
            "clearance": "internal",
            "env": "production",
        },
        "classification": "internal",
        "folder_id": "folder_ms_open",
        "file": {
            "filename": "report.pdf",
            "mime_type": "application/pdf",
            "size_bytes": len(raw),
            "content_base64": base64.b64encode(raw).decode("ascii"),
        },
    }


def test_process_document_full_pipeline():
    raw = b"%PDF-1.4 pipeline test"
    result = process_document(
        _request(raw),
        folder_acl=_folder_acl(),
        dedup_store=DedupStore(),
        raw_bytes=raw,
    )
    assert result.ingest_response["ingest_status"] == "processing"
    assert result.ocr_result is not None
    assert result.ocr_result["ocr_status"] == "completed"
    assert result.chunks is not None
    assert len(result.chunks) == 1
    assert result.chunks[0]["folder_id"] == "folder_ms_open"
