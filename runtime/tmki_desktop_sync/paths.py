from __future__ import annotations

import os
import re
from pathlib import Path


def _surname_from_display_name(display_name: str) -> str:
    """Фамилия — первое слово display_name (кириллица)."""
    parts = display_name.strip().split()
    if not parts:
        raise ValueError("display_name пустой")
    return parts[0]


def desktop_folder_for_employee(
    display_name: str,
    *,
    desktop_root: Path | None = None,
) -> Path:
    root = desktop_root or Path(os.environ.get("USERPROFILE", "~")).expanduser() / "Desktop"
    surname = _surname_from_display_name(display_name)
    return root / surname


def default_server_path(employee_id: str, *, base: Path | None = None) -> Path:
    server_base = base or Path(
        os.environ.get("TMKI_SYNC_SERVER_ROOT", Path(__file__).resolve().parents[1] / "artifacts" / "desktop-sync")
    )
    safe_id = re.sub(r"[^\w\-]", "_", employee_id)
    return server_base / safe_id
