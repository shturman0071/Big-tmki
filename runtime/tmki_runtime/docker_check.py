"""Проверка Docker daemon для finalize/pgvector."""

from __future__ import annotations

import shutil
import subprocess


def docker_daemon_ready(*, timeout_sec: int = 10) -> tuple[bool, str]:
    if shutil.which("docker") is None:
        return False, "docker CLI not found"
    try:
        proc = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return False, "docker info timeout"
    except OSError as exc:
        return False, str(exc)
    if proc.returncode == 0:
        return True, "daemon running"
    detail = (proc.stderr or proc.stdout or "").strip().splitlines()
    return False, detail[-1] if detail else f"exit {proc.returncode}"
