from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tmki_desktop_sync.paths import default_server_path, desktop_folder_for_employee


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ProvisionResult:
    employee_id: str
    display_name: str
    desktop_path: str
    server_path: str
    folder_id: str
    created_desktop: bool
    manifest_path: str


def provision_employee_desktop(
    *,
    employee_id: str,
    display_name: str,
    folder_id: str | None = None,
    desktop_root: Path | None = None,
    server_base: Path | None = None,
    manifest_dir: Path | None = None,
) -> ProvisionResult:
    """
    #44: создать папку Desktop\\{фамилия} и манифест sync для сотрудника.
    """
    desk = desktop_folder_for_employee(display_name, desktop_root=desktop_root)
    server = default_server_path(employee_id, base=server_base)
    fid = folder_id or f"folder_desktop_{employee_id}"

    created = False
    if not desk.is_dir():
        desk.mkdir(parents=True, exist_ok=True)
        created = True
    server.mkdir(parents=True, exist_ok=True)

    out_dir = manifest_dir or (Path(__file__).resolve().parents[1] / "artifacts" / "desktop-sync" / "manifests")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / f"{employee_id}.json"

    manifest: dict[str, Any] = {
        "schema_version": "0.1",
        "employee_id": employee_id,
        "folder_id": fid,
        "surname_folder_name": desk.name,
        "desktop_path": str(desk),
        "server_path": str(server),
        "sync_interval_sec": 5,
        "direction": "desktop_to_server",
        "conflict_policy": "server_wins",
        "status": "active",
        "provisioned_at": _now_iso(),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return ProvisionResult(
        employee_id=employee_id,
        display_name=display_name,
        desktop_path=str(desk),
        server_path=str(server),
        folder_id=fid,
        created_desktop=created,
        manifest_path=str(manifest_path),
    )
