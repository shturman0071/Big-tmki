from __future__ import annotations

from tmki_desktop_sync.paths import desktop_folder_for_employee, default_server_path
from tmki_desktop_sync.provision import ProvisionResult, provision_employee_desktop
from tmki_desktop_sync.watcher import DesktopSyncWatcher, run_sync_once

__all__ = [
    "DesktopSyncWatcher",
    "desktop_folder_for_employee",
    "default_server_path",
    "provision_employee_desktop",
    "ProvisionResult",
    "run_sync_once",
]
