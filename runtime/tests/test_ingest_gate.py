from datetime import date
from pathlib import Path

import pytest

from tmki_ingest import validate_delete, validate_ingest
from tmki_rag import FolderAclContext, load_folder_catalog, load_folder_grants, resolve_folder_id

ROOT = Path(__file__).resolve().parents[2]
FOLDERS_FILE = ROOT / "schemas/document/examples/satimol-folders.example.json"
GRANTS_FILE = ROOT / "schemas/org/examples/satimol-folder-grants.example.json"
AS_OF = date(2025, 9, 10)


@pytest.fixture
def folder_acl():
    return FolderAclContext.from_catalog(
        load_folder_catalog(FOLDERS_FILE),
        load_folder_grants(GRANTS_FILE),
        as_of=AS_OF,
    )


def _ctx(employee_id: str, role: str, clearance: str = "restricted") -> dict:
    return {
        "company_id": "company_tmki_ru",
        "project_id": "project_satimol",
        "department_id": "dept_markscheider",
        "project_role": role,
        "employee_id": employee_id,
        "clearance": clearance,
        "env": "production",
    }


def test_resolve_folder_id_longest_prefix(folder_acl):
    folders = list(folder_acl.folders_by_id.values())
    path = "/sites/Satimol/Markscheider/Общие/отчёт_2025.pdf"
    assert resolve_folder_id(path, folders) == "folder_ms_open"
    assert resolve_folder_id("/sites/Satimol/Markscheider/Договоры/nda.pdf", folders) == "folder_ms_contracts"


def test_employee_upload_to_open_folder(folder_acl):
    result = validate_ingest(
        _ctx("emp_staff_x", "Сотрудник подразделения"),
        "internal",
        folder_acl,
        source_path="/sites/Satimol/Markscheider/Общие/report.pdf",
    )
    assert result.allowed is True
    assert result.folder_id == "folder_ms_open"
    assert result.resolved_from_path is True


def test_employee_cannot_upload_to_contracts_without_grant(folder_acl):
    result = validate_ingest(
        _ctx("emp_staff_x", "Сотрудник подразделения", "confidential"),
        "confidential",
        folder_acl,
        folder_id="folder_ms_contracts",
    )
    assert result.allowed is False
    assert result.error_code == "INGEST_FOLDER_DENIED"


def test_employee_upload_contracts_with_write_grant(folder_acl):
    grants = load_folder_grants(GRANTS_FILE)
    grants.append(
        {
            "schema_version": "0.1",
            "grant_id": "grant_write_ivanov",
            "grant_type": "grant",
            "employee_id": "emp_ivanov_a",
            "folder_id": "folder_ms_contracts",
            "department_id": "dept_markscheider",
            "granted_by_employee_id": "emp_litovsky_d",
            "actions": ["read", "write"],
            "valid_from": "2025-09-01",
            "status": "active",
        }
    )
    acl = FolderAclContext.from_catalog(load_folder_catalog(FOLDERS_FILE), grants, as_of=AS_OF)
    result = validate_ingest(
        _ctx("emp_ivanov_a", "Сотрудник подразделения", "confidential"),
        "confidential",
        acl,
        folder_id="folder_ms_contracts",
    )
    assert result.allowed is True


def test_delete_denied_for_employee(folder_acl):
    result = validate_delete(
        _ctx("emp_petrov_v", "Сотрудник подразделения"),
        folder_acl,
        folder_id="folder_ms_open",
    )
    assert result.allowed is False
    assert result.error_code == "INGEST_DELETE_DENIED"


def test_delete_allowed_for_dept_head(folder_acl):
    result = validate_delete(
        _ctx("emp_litovsky_d", "Chefmarkscheider"),
        folder_acl,
        folder_id="folder_ms_open",
    )
    assert result.allowed is True
