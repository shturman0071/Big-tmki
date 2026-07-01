import base64
from datetime import date
from pathlib import Path

import pytest

from tmki_ingest import DedupStore, accept_ingest, check_dedup, compute_content_hash
from tmki_rag import FolderAclContext, load_folder_catalog, load_folder_grants

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def folder_acl():
    return FolderAclContext.from_catalog(
        load_folder_catalog(ROOT / "schemas/document/examples/satimol-folders.example.json"),
        load_folder_grants(ROOT / "schemas/org/examples/satimol-folder-grants.example.json"),
        as_of=date(2025, 9, 10),
    )


def _ctx():
    return {
        "company_id": "company_tmki_ru",
        "project_id": "project_satimol",
        "department_id": "dept_markscheider",
        "project_role": "Сотрудник подразделения",
        "employee_id": "emp_staff_x",
        "clearance": "internal",
        "env": "production",
    }


def test_compute_content_hash_stable():
    data = b"test pdf bytes"
    assert compute_content_hash(data).startswith("sha256:")
    assert compute_content_hash(data) == compute_content_hash(data)


def test_dedup_skips_same_hash():
    store = DedupStore()
    h = compute_content_hash(b"same")
    first = check_dedup(
        store,
        company_id="company_tmki_ru",
        project_id="project_satimol",
        content_hash=h,
        classification="internal",
        new_doc_id="doc_a",
    )
    second = check_dedup(
        store,
        company_id="company_tmki_ru",
        project_id="project_satimol",
        content_hash=h,
        classification="internal",
    )
    assert first.ingest_status == "accepted"
    assert second.ingest_status == "duplicate"
    assert second.dedup_action == "skipped_processing"
    assert second.matched_doc_id == "doc_a"


def test_accept_ingest_new_document(folder_acl):
    raw = b"%PDF-1.4 satimol test"
    request = {
        "policy_context": _ctx(),
        "classification": "internal",
        "provenance": {
            "source_path": "/sites/Satimol/Markscheider/Общие/report.pdf",
        },
        "file": {
            "filename": "report.pdf",
            "mime_type": "application/pdf",
            "size_bytes": len(raw),
            "content_base64": base64.b64encode(raw).decode("ascii"),
        },
    }
    result = accept_ingest(request, folder_acl=folder_acl, dedup_store=DedupStore(), raw_bytes=raw)
    assert result.ingest_status == "accepted"
    assert result.folder_id == "folder_ms_open"
    assert result.doc_id


def test_accept_ingest_duplicate(folder_acl):
    raw = b"duplicate content"
    store = DedupStore()
    request = {
        "policy_context": _ctx(),
        "classification": "internal",
        "folder_id": "folder_ms_open",
        "file": {"content_base64": base64.b64encode(raw).decode("ascii")},
    }
    first = accept_ingest(request, folder_acl=folder_acl, dedup_store=store, raw_bytes=raw)
    second = accept_ingest(request, folder_acl=folder_acl, dedup_store=store, raw_bytes=raw)
    assert first.ingest_status == "accepted"
    assert second.ingest_status == "duplicate"
    assert second.dedup_action == "skipped_processing"
