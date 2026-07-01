from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

from tmki_rag.folders import load_folder_catalog

_DEPT_HEAD_ROLES = frozenset(
    {
        "Chefmarkscheider",
        "Начальник подразделения",
        "Начальник участка",
    }
)


class GrantServiceError(Exception):
    pass


def is_dept_head(project_role: str) -> bool:
    return project_role in _DEPT_HEAD_ROLES


@dataclass
class GrantStore:
    path: Path
    grants: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> GrantStore:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(path=path, grants=list(data.get("grants", [])))
        return cls(path=path, grants=[])

    def save(self) -> None:
        payload = {
            "schema_version": "0.1",
            "description": "EmployeeFolderGrant store (managed by tmki_admin)",
            "grants": self.grants,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def active_for_employee(self, employee_id: str, *, as_of: date | None = None) -> list[dict[str, Any]]:
        from tmki_rag.folders import _is_active  # noqa: PLC2701

        as_of = as_of or date.today()
        return [
            g
            for g in self.grants
            if g.get("employee_id") == employee_id
            and g.get("status") == "active"
            and _is_active(g, as_of)
        ]


@dataclass
class GrantService:
    store: GrantStore
    folders: list[dict[str, Any]]

    def _folder(self, folder_id: str) -> dict[str, Any]:
        for folder in self.folders:
            if folder.get("folder_id") == folder_id:
                return folder
        raise GrantServiceError(f"Папка не найдена: {folder_id}")

    def _assert_granter(self, granter: dict[str, Any], folder: dict[str, Any]) -> None:
        if not is_dept_head(granter.get("project_role", "")):
            raise GrantServiceError("Только начальник подразделения может управлять доступами")
        if granter.get("department_id") != folder.get("department_id"):
            raise GrantServiceError("Нельзя управлять папками чужого подразделения")

    def _revoke_matching(
        self,
        employee_id: str,
        folder_id: str,
        grant_type: str,
    ) -> None:
        for grant in self.store.grants:
            if (
                grant.get("employee_id") == employee_id
                and grant.get("folder_id") == folder_id
                and grant.get("grant_type") == grant_type
                and grant.get("status") == "active"
            ):
                grant["status"] = "revoked"

    def set_deny_read(
        self,
        granter: dict[str, Any],
        *,
        employee_id: str,
        folder_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        folder = self._folder(folder_id)
        self._assert_granter(granter, folder)
        if folder.get("access_tier") != "department_open":
            raise GrantServiceError("Deny применим к открытым папкам отдела (department_open)")

        self._revoke_matching(employee_id, folder_id, "deny")
        entry = {
            "schema_version": "0.1",
            "grant_id": f"deny_{folder_id}_{employee_id}_{uuid4().hex[:8]}",
            "grant_type": "deny",
            "employee_id": employee_id,
            "folder_id": folder_id,
            "department_id": folder["department_id"],
            "granted_by_employee_id": granter["employee_id"],
            "actions": ["read"],
            "valid_from": date.today().isoformat(),
            "status": "active",
        }
        if reason:
            entry["reason"] = reason
        self.store.grants.append(entry)
        self.store.save()
        return entry

    def set_grant(
        self,
        granter: dict[str, Any],
        *,
        employee_id: str,
        folder_id: str,
        actions: list[str],
        valid_to: str | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        folder = self._folder(folder_id)
        self._assert_granter(granter, folder)
        tier = folder.get("access_tier", "department_open")
        if tier not in ("department_restricted", "grant_only"):
            raise GrantServiceError("Grant для закрытых папок (restricted / grant_only)")

        if "delete" in actions:
            raise GrantServiceError("delete нельзя выдавать через grant")

        self._revoke_matching(employee_id, folder_id, "grant")
        entry = {
            "schema_version": "0.1",
            "grant_id": f"grant_{folder_id}_{employee_id}_{uuid4().hex[:8]}",
            "grant_type": "grant",
            "employee_id": employee_id,
            "folder_id": folder_id,
            "department_id": folder["department_id"],
            "granted_by_employee_id": granter["employee_id"],
            "actions": sorted(set(actions)),
            "valid_from": date.today().isoformat(),
            "status": "active",
        }
        if valid_to:
            entry["valid_to"] = valid_to
        if reason:
            entry["reason"] = reason
        self.store.grants.append(entry)
        self.store.save()
        return entry

    def revoke(
        self,
        granter: dict[str, Any],
        *,
        employee_id: str,
        folder_id: str,
        grant_type: str,
    ) -> bool:
        folder = self._folder(folder_id)
        self._assert_granter(granter, folder)
        found = False
        for grant in self.store.grants:
            if (
                grant.get("employee_id") == employee_id
                and grant.get("folder_id") == folder_id
                and grant.get("grant_type") == grant_type
                and grant.get("status") == "active"
            ):
                grant["status"] = "revoked"
                found = True
        if found:
            self.store.save()
        return found

    def folders_for_department(self, department_id: str) -> list[dict[str, Any]]:
        return [
            f
            for f in self.folders
            if f.get("department_id") == department_id and f.get("status", "active") == "active"
        ]


def default_satimol_paths(root: Path) -> tuple[Path, Path]:
    return (
        root / "schemas/document/examples/satimol-folders.example.json",
        root / "schemas/org/examples/satimol-folder-grants.example.json",
    )


def open_grant_service(root: Path) -> GrantService:
    folders_path, grants_path = default_satimol_paths(root)
    return GrantService(
        store=GrantStore.load(grants_path),
        folders=load_folder_catalog(folders_path),
    )
