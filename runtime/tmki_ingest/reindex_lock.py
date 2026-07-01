from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_lock(lock_path: Path) -> dict[str, Any] | None:
    if not lock_path.is_file():
        return None
    try:
        return json.loads(lock_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def acquire_reindex_lock(lock_path: Path, *, force: bool = False) -> dict[str, Any] | None:
    """
    Эксклюзивная блокировка re-index (один процесс на архив).
    Возвращает None при успехе, иначе данные активной блокировки.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_lock(lock_path)
    if existing and not force:
        pid = int(existing.get("pid") or 0)
        if process_alive(pid):
            return existing

    payload = {
        "schema_version": "0.1",
        "pid": os.getpid(),
        "started_at": _now_iso(),
    }
    lock_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return None


def release_reindex_lock(lock_path: Path) -> None:
    existing = read_lock(lock_path)
    if existing and int(existing.get("pid") or 0) == os.getpid() and lock_path.is_file():
        lock_path.unlink(missing_ok=True)
