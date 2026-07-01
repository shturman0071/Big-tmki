from datetime import date
from pathlib import Path

import pytest

from tmki_policy import PolicyContextError, build_policy_context, load_org_snapshot

SNAPSHOT = Path(__file__).resolve().parents[2] / "schemas/org/examples/satimol-snapshot.example.json"


@pytest.fixture
def snapshot():
    return load_org_snapshot(SNAPSHOT)


def test_chefmarkscheider_policy_context(snapshot):
    ctx = build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )
    assert ctx == {
        "company_id": "company_tmki_ru",
        "project_id": "project_satimol",
        "department_id": "dept_markscheider",
        "project_role": "Chefmarkscheider",
        "employee_id": "emp_litovsky_d",
        "clearance": "restricted",
        "env": "production",
    }


def test_projektleiter_without_department(snapshot):
    ctx = build_policy_context(
        snapshot,
        employee_id="emp_neff_a",
        env="staging",
        as_of=date(2025, 9, 10),
    )
    assert ctx["project_role"] == "Projektleiter"
    assert "department_id" not in ctx


def test_unknown_employee(snapshot):
    with pytest.raises(PolicyContextError):
        build_policy_context(snapshot, employee_id="emp_nobody", env="production")
