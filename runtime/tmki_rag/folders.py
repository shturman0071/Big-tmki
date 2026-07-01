from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

# Начальник подразделения / участка — доступ к закрытым папкам своего dept без grant
_DEPT_HEAD_ROLES = frozenset(
    {
        "Chefmarkscheider",
        "Начальник подразделения",
        "Начальник участка",
    }
)

# Руководство проекта — обход grant_only в рамках project (RLS clearance всё ещё действует)
_LEADERSHIP_ROLES = frozenset(
    {
        "Direktor",
        "Projektleiter",
        "Projektleiter (Design)",
        "group_admin",
    }
)


def load_folder_catalog(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("folders", data if isinstance(data, list) else [])


def load_folder_grants(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("grants", data if isinstance(data, list) else [])


def _is_active(entry: dict[str, Any], as_of: date) -> bool:
    if entry.get("status") != "active":
        return False
    valid_from = date.fromisoformat(entry["valid_from"])
    if valid_from > as_of:
        return False
    valid_to = entry.get("valid_to")
    if valid_to and date.fromisoformat(valid_to) < as_of:
        return False
    return True


@dataclass
class FolderAclContext:
    """Каталог папок + grant/deny для server-side folder ACL (#21)."""

    folders_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    grants: list[dict[str, Any]] = field(default_factory=list)
    as_of: date = field(default_factory=date.today)

    @classmethod
    def from_catalog(
        cls,
        folders: list[dict[str, Any]],
        grants: list[dict[str, Any]] | None = None,
        *,
        as_of: date | None = None,
    ) -> FolderAclContext:
        active_folders = {
            f["folder_id"]: f
            for f in folders
            if f.get("status", "active") == "active"
        }
        return cls(
            folders_by_id=active_folders,
            grants=grants or [],
            as_of=as_of or date.today(),
        )

    def _matching_entries(
        self,
        employee_id: str,
        folder_id: str,
        grant_type: str,
        action: str,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for entry in self.grants:
            if entry.get("employee_id") != employee_id:
                continue
            if entry.get("folder_id") != folder_id:
                continue
            if entry.get("grant_type") != grant_type:
                continue
            if action not in entry.get("actions", []):
                continue
            if not _is_active(entry, self.as_of):
                continue
            result.append(entry)
        return result

    def has_deny(self, employee_id: str, folder_id: str, action: str = "read") -> bool:
        return bool(self._matching_entries(employee_id, folder_id, "deny", action))

    def has_grant(self, employee_id: str, folder_id: str, action: str = "read") -> bool:
        return bool(self._matching_entries(employee_id, folder_id, "grant", action))

    def allows_read(self, chunk: dict[str, Any], policy_context: dict[str, Any]) -> bool:
        folder_id = chunk.get("folder_id")
        if not folder_id:
            return True

        folder = self.folders_by_id.get(folder_id)
        if not folder:
            return False

        employee_id = policy_context.get("employee_id", "")
        role = policy_context.get("project_role", "")

        if self.has_deny(employee_id, folder_id, "read"):
            return False

        if role in _LEADERSHIP_ROLES:
            return True

        if role in _DEPT_HEAD_ROLES and policy_context.get("department_id") == folder.get("department_id"):
            return True

        tier = folder.get("access_tier", "department_open")
        if tier == "department_open":
            return True

        if tier in ("department_restricted", "grant_only"):
            return self.has_grant(employee_id, folder_id, "read")

        return False

    def allows_delete(self, folder_id: str, policy_context: dict[str, Any]) -> bool:
        """Delete: рядовой сотрудник — запрещён; начальник dept — разрешён (ORG_MODEL §Делегирование)."""
        role = policy_context.get("project_role", "")
        if role in _LEADERSHIP_ROLES:
            return True
        if role in _DEPT_HEAD_ROLES:
            folder = self.folders_by_id.get(folder_id)
            if folder and policy_context.get("department_id") == folder.get("department_id"):
                return True
        if role == "Сотрудник подразделения":
            return False
        return role in _DEPT_HEAD_ROLES
