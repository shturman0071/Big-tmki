from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from tmki_policy.errors import PolicyContextError

_VALID_ENVS = frozenset({"development", "staging", "production"})
_VALID_CLEARANCE = frozenset({"public", "internal", "restricted", "confidential"})


def load_org_snapshot(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _index_by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {item[key]: item for item in items}


def _active_assignments(
    assignments: list[dict[str, Any]],
    employee_id: str,
    as_of: date,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for a in assignments:
        if a.get("employee_id") != employee_id or a.get("status") != "active":
            continue
        valid_from = date.fromisoformat(a["valid_from"])
        if valid_from > as_of:
            continue
        valid_to = a.get("valid_to")
        if valid_to and date.fromisoformat(valid_to) < as_of:
            continue
        result.append(a)
    return result


def build_policy_context(
    snapshot: dict[str, Any],
    *,
    employee_id: str,
    env: str,
    project_id: str | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """
    Собирает policy_context по активным Assignment (MUST server-side).
    См. ORG_MODEL.md, schemas/runtime/common.schema.json.
    """
    if env not in _VALID_ENVS:
        raise PolicyContextError(f"Недопустимый env: {env}")

    as_of = as_of or date.today()
    employees = _index_by(snapshot.get("employees", []), "employee_id")
    employee = employees.get(employee_id)
    if not employee or employee.get("status") != "active":
        raise PolicyContextError(f"Сотрудник не найден или неактивен: {employee_id}")

    assignments = _active_assignments(snapshot.get("assignments", []), employee_id, as_of)
    project_assignments = [a for a in assignments if a.get("assignment_type") == "project_role"]
    if not project_assignments:
        raise PolicyContextError(f"Нет активного project_role для {employee_id}")

    if project_id:
        project_assignments = [a for a in project_assignments if a.get("project_id") == project_id]
        if not project_assignments:
            raise PolicyContextError(f"Нет назначения на проект {project_id}")

    # при нескольких — берём первое (в проде: явный выбор сессии)
    assignment = project_assignments[0]

    clearance = employee.get("clearance", "internal")
    if clearance not in _VALID_CLEARANCE:
        raise PolicyContextError(f"Недопустимый clearance: {clearance}")

    ctx: dict[str, Any] = {
        "company_id": assignment.get("company_id") or employee["company_id"],
        "project_id": assignment["project_id"],
        "project_role": assignment["project_role"],
        "employee_id": employee_id,
        "clearance": clearance,
        "env": env,
    }

    department_id = assignment.get("department_id")
    if department_id:
        ctx["department_id"] = department_id

    contractor_id = employee.get("contractor_id")
    if contractor_id:
        ctx["contractor_id"] = contractor_id

    companies = _index_by(snapshot.get("companies", []), "company_id")
    company = companies.get(ctx["company_id"])
    if company and company.get("company_group_id"):
        if assignment.get("project_role") == "group_admin":
            ctx["company_group_id"] = company["company_group_id"]

    return ctx
