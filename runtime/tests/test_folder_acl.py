import json
from datetime import date
from pathlib import Path

from tmki_rag import FolderAclContext, load_folder_catalog, load_folder_grants, rag_search

ROOT = Path(__file__).resolve().parents[2]
CHUNKS_FILE = ROOT / "schemas/document/examples/satimol-chunks.example.json"
FOLDERS_FILE = ROOT / "schemas/document/examples/satimol-folders.example.json"
GRANTS_FILE = ROOT / "schemas/org/examples/satimol-folder-grants.example.json"
AS_OF = date(2025, 9, 10)


def _chunks():
    return json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))["chunks"]


def _folder_acl() -> FolderAclContext:
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


def _search(ctx: dict, query: str = "маркшейдерская съёмка"):
    return rag_search(
        {
            "schema_version": "0.1",
            "trace_id": "trace-folder-acl",
            "query": query,
            "top_k": 8,
            "policy_context": ctx,
        },
        _chunks(),
        folder_acl=_folder_acl(),
    )


def test_employee_deny_on_open_folder():
    resp = _search(_ctx("emp_petrov_v", "Сотрудник подразделения"))
    doc_ids = {r["doc_id"] for r in resp["results"]}
    assert "doc_markscheider_ks_2025" not in doc_ids


def test_grant_opens_contracts_folder():
    resp = _search(_ctx("emp_ivanov_a", "Сотрудник подразделения", "confidential"))
    doc_ids = {r["doc_id"] for r in resp["results"]}
    assert "doc_ms_subcontract_ks" in doc_ids


def test_no_grant_no_contracts_for_employee():
    resp = _search(_ctx("emp_staff_x", "Сотрудник подразделения", "confidential"))
    doc_ids = {r["doc_id"] for r in resp["results"]}
    assert "doc_ms_subcontract_ks" not in doc_ids


def test_dept_head_sees_grant_only_with_clearance():
    resp = _search(_ctx("emp_litovsky_d", "Chefmarkscheider", "confidential"))
    doc_ids = {r["doc_id"] for r in resp["results"]}
    assert "doc_ms_subcontract_ks" in doc_ids
    assert "doc_markscheider_ks_2025" in doc_ids


def test_dept_head_blocked_by_clearance_on_confidential():
    resp = _search(_ctx("emp_litovsky_d", "Chefmarkscheider", "restricted"))
    doc_ids = {r["doc_id"] for r in resp["results"]}
    assert "doc_ms_subcontract_ks" not in doc_ids
    assert "doc_markscheider_ks_2025" in doc_ids


def test_delete_policy():
    acl = _folder_acl()
    head = _ctx("emp_litovsky_d", "Chefmarkscheider")
    staff = _ctx("emp_petrov_v", "Сотрудник подразделения")
    assert acl.allows_delete("folder_ms_open", head) is True
    assert acl.allows_delete("folder_ms_open", staff) is False
