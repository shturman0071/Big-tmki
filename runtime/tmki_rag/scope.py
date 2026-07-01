from __future__ import annotations

from typing import Any

# Маппинг project_role → department_scope (ORG_MODEL + tool-gating v0.1)
_ROLE_DEPARTMENT_SCOPE: dict[str, str] = {
    "Direktor": "S_project",
    "Projektleiter": "S_project",
    "Projektleiter (Design)": "S_project",
    "Generalprojektant": "S_project",
    "ГИП": "S_dept_tree",
    "Главный инженер проекта": "S_dept_tree",
    "Hauptingenieur": "S_dept_tree",
    "Chefmarkscheider": "S_dept",
    "Начальник участка": "S_dept",
    "Подрядчик (external)": "S_dept",
    "group_admin": "S_project",
}


def resolve_department_scope(policy_context: dict[str, Any]) -> str:
    role = policy_context.get("project_role", "")
    return _ROLE_DEPARTMENT_SCOPE.get(role, "S_project")
