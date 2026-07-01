from datetime import date
from pathlib import Path

import pytest

from tmki_admin.grants_service import GrantService, GrantStore, GrantServiceError
from tmki_rag import load_folder_catalog

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def service(tmp_path: Path):
    folders = load_folder_catalog(ROOT / "schemas/document/examples/satimol-folders.example.json")
    grants_path = tmp_path / "grants.json"
    store = GrantStore.load(ROOT / "schemas/org/examples/satimol-folder-grants.example.json")
    store.path = grants_path
    return GrantService(store=store, folders=folders)


def _granter():
    return {
        "employee_id": "emp_litovsky_d",
        "project_role": "Chefmarkscheider",
        "department_id": "dept_markscheider",
        "company_id": "company_tmki_ru",
        "project_id": "project_satimol",
    }


def test_dept_head_can_deny_open_folder(service):
    entry = service.set_deny_read(
        _granter(),
        employee_id="emp_staff_x",
        folder_id="folder_ms_open",
    )
    assert entry["grant_type"] == "deny"
    active = service.store.active_for_employee("emp_staff_x", as_of=date.today())
    assert any(g["grant_id"] == entry["grant_id"] for g in active)


def test_non_head_cannot_grant(service):
    with pytest.raises(GrantServiceError, match="начальник"):
        service.set_grant(
            {
                "employee_id": "emp_staff_x",
                "project_role": "Сотрудник подразделения",
                "department_id": "dept_markscheider",
            },
            employee_id="emp_ivanov_a",
            folder_id="folder_ms_contracts",
            actions=["read"],
        )


def test_grant_closed_folder(service):
    entry = service.set_grant(
        _granter(),
        employee_id="emp_ivanov_a",
        folder_id="folder_ms_contracts",
        actions=["read", "write"],
    )
    assert "write" in entry["actions"]
    assert service.store.path.exists()


def test_revoke_grant(service):
    service.set_deny_read(_granter(), employee_id="emp_petrov_v", folder_id="folder_ms_open")
    ok = service.revoke(
        _granter(),
        employee_id="emp_petrov_v",
        folder_id="folder_ms_open",
        grant_type="deny",
    )
    assert ok is True
