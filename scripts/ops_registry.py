#!/usr/bin/env python3
"""Реестр фоновых задач TMKI (для watch_tmki_ops.py)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OPS_PATH = Path(__file__).resolve().parents[1] / "runtime" / "artifacts" / "demo" / "ops-jobs.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_jobs() -> dict[str, Any]:
    if not OPS_PATH.is_file():
        return {"updated_at": None, "jobs": []}
    try:
        return json.loads(OPS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"updated_at": None, "jobs": []}


def save_jobs(data: dict[str, Any]) -> None:
    OPS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    OPS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_job(
    job_id: str,
    *,
    label: str,
    status: str,
    progress: float | None = None,
    detail: str | None = None,
    pid: int | None = None,
) -> None:
    data = load_jobs()
    jobs: list[dict[str, Any]] = data.get("jobs") or []
    found = False
    for job in jobs:
        if job.get("id") == job_id:
            job["label"] = label
            job["status"] = status
            if progress is not None:
                job["progress"] = progress
            if detail is not None:
                job["detail"] = detail
            if pid is not None:
                job["pid"] = pid
            if status == "running" and not job.get("started_at"):
                job["started_at"] = _now()
            if status in ("done", "failed", "skipped"):
                job["finished_at"] = _now()
            found = True
            break
    if not found:
        jobs.append(
            {
                "id": job_id,
                "label": label,
                "status": status,
                "progress": progress,
                "detail": detail,
                "pid": pid or os.getpid(),
                "started_at": _now() if status == "running" else None,
            }
        )
    data["jobs"] = jobs[-20:]
    save_jobs(data)
