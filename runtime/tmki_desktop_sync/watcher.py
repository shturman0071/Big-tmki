from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class SyncFileRecord:
    relative_path: str
    size: int
    mtime_ns: int
    action: str  # copied | skipped | error


class DesktopSyncWatcher:
    """Синхронизация Desktop\\{фамилия} → локальный сервер каждые N секунд."""

    def __init__(
        self,
        *,
        desktop_path: Path,
        server_path: Path,
        employee_id: str,
        interval_sec: int | None = None,
        on_file_synced: Callable[[Path, Path], None] | None = None,
    ) -> None:
        self.desktop_path = desktop_path
        self.server_path = server_path
        self.employee_id = employee_id
        self.interval_sec = interval_sec or int(os.environ.get("TMKI_DESKTOP_SYNC_INTERVAL_SEC", "5"))
        self.on_file_synced = on_file_synced
        self.state_path = server_path / ".sync-state.json"

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.is_file():
            return {"files": {}}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _save_state(self, state: dict[str, Any]) -> None:
        self.server_path.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = _now_iso()
        state["employee_id"] = self.employee_id
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def sync_once(self) -> list[SyncFileRecord]:
        if not self.desktop_path.is_dir():
            return []

        state = self._load_state()
        files_state: dict[str, Any] = state.setdefault("files", {})
        results: list[SyncFileRecord] = []

        for src in self.desktop_path.rglob("*"):
            if not src.is_file() or src.name.startswith("~$"):
                continue
            rel = str(src.relative_to(self.desktop_path)).replace("\\", "/")
            stat = src.stat()
            prev = files_state.get(rel)
            signature = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
            if prev == signature:
                results.append(SyncFileRecord(rel, stat.st_size, stat.st_mtime_ns, "skipped"))
                continue

            dest = self.server_path / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src, dest)
                files_state[rel] = signature
                results.append(SyncFileRecord(rel, stat.st_size, stat.st_mtime_ns, "copied"))
                if self.on_file_synced:
                    self.on_file_synced(src, dest)
            except OSError as exc:
                results.append(SyncFileRecord(rel, stat.st_size, stat.st_mtime_ns, f"error:{exc}"))

        self._save_state(state)
        return results

    def run_loop(self, *, max_iterations: int | None = None) -> None:
        n = 0
        while max_iterations is None or n < max_iterations:
            self.sync_once()
            n += 1
            time.sleep(self.interval_sec)


def run_sync_once(
    *,
    display_name: str,
    employee_id: str,
    desktop_path: Path | None = None,
    server_path: Path | None = None,
) -> list[SyncFileRecord]:
    from tmki_desktop_sync.paths import default_server_path, desktop_folder_for_employee

    desk = desktop_path or desktop_folder_for_employee(display_name)
    server = server_path or default_server_path(employee_id)
    watcher = DesktopSyncWatcher(
        desktop_path=desk,
        server_path=server,
        employee_id=employee_id,
    )
    return watcher.sync_once()
