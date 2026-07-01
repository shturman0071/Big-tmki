from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

SyncAction = Literal[
    "add_read",
    "remove_read",
    "add_write",
    "remove_write",
]


@dataclass(frozen=True)
class SharePointPermissionChange:
    folder_id: str
    physical_path: str
    storage_backend: str
    employee_id: str
    action: SyncAction
    grant_id: str | None = None


def _folder_map(folders: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {f["folder_id"]: f for f in folders if f.get("status", "active") != "inactive"}


def _desired_permissions(
    grants: list[dict[str, Any]],
    folders: list[dict[str, Any]],
) -> dict[tuple[str, str], set[str]]:
    """(employee_id, folder_id) -> {'read','write'} from active grants/denies."""
    folders_by_id = _folder_map(folders)
    desired: dict[tuple[str, str], set[str]] = {}

    for grant in grants:
        if grant.get("status") != "active":
            continue
        folder_id = grant.get("folder_id", "")
        folder = folders_by_id.get(folder_id)
        if not folder:
            continue
        employee_id = grant["employee_id"]
        key = (employee_id, folder_id)
        tier = folder.get("access_tier", "department_open")

        if grant.get("grant_type") == "deny":
            desired[key] = set()
            continue

        if grant.get("grant_type") == "grant":
            desired[key] = set(grant.get("actions", []))

        if tier == "department_open" and grant.get("grant_type") != "deny":
            desired.setdefault(key, {"read", "write"})

    return desired


def build_sync_plan(
    grants: list[dict[str, Any]],
    folders: list[dict[str, Any]],
) -> list[SharePointPermissionChange]:
    """
    План изменений ACL SharePoint из активных EmployeeFolderGrant.
    MVP: один change на grant; production — diff с текущим SP state.
    """
    folders_by_id = _folder_map(folders)
    changes: list[SharePointPermissionChange] = []

    for grant in grants:
        if grant.get("status") != "active":
            continue
        folder_id = grant.get("folder_id", "")
        folder = folders_by_id.get(folder_id)
        if not folder or folder.get("storage_backend") != "sharepoint":
            continue

        employee_id = grant["employee_id"]
        physical_path = folder["physical_path"]
        grant_id = grant.get("grant_id")

        if grant.get("grant_type") == "deny":
            changes.append(
                SharePointPermissionChange(
                    folder_id=folder_id,
                    physical_path=physical_path,
                    storage_backend="sharepoint",
                    employee_id=employee_id,
                    action="remove_read",
                    grant_id=grant_id,
                )
            )
            continue

        for action in grant.get("actions", []):
            sp_action: SyncAction = "add_read" if action == "read" else "add_write"
            changes.append(
                SharePointPermissionChange(
                    folder_id=folder_id,
                    physical_path=physical_path,
                    storage_backend="sharepoint",
                    employee_id=employee_id,
                    action=sp_action,
                    grant_id=grant_id,
                )
            )

    return changes


class StubSharePointAdapter:
    """Заглушка Graph API / SharePoint REST до подключения production."""

    def __init__(self) -> None:
        self.applied: list[SharePointPermissionChange] = []

    def apply(self, plan: list[SharePointPermissionChange]) -> dict[str, Any]:
        self.applied = list(plan)
        return {
            "adapter": "stub",
            "changes_applied": len(plan),
            "items": [
                {
                    "path": c.physical_path,
                    "employee_id": c.employee_id,
                    "action": c.action,
                }
                for c in plan
            ],
        }
