"""Статус pipeline re-index → finalize (read-only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _artifact_flags(artifacts_dir: Path) -> dict[str, bool]:
    names = [
        "reindex-complete-latest.json",
        "reindex-ops-bundle-latest.json",
        "reindex-handoff.txt",
        "finalize-done.json",
        "finalize-summary-latest.json",
        "finalize-handoff.txt",
        "finalize-ops-bundle-latest.json",
        "quality-benchmark-final.json",
    ]
    return {name: (artifacts_dir / name).is_file() for name in names}


def _pipeline_phase(*, ready_for_finalize: bool, finalize_done: bool, complete: bool) -> str:
    if finalize_done:
        return "post_finalize"
    if ready_for_finalize:
        return "ready_for_finalize"
    if complete:
        return "reindex_complete_lock"
    return "reindexing"


def _next_step(
    *,
    phase: str,
    docker_ready: bool,
) -> str:
    if phase == "post_finalize":
        return "post_finalize_checklist.ps1"
    if phase in ("ready_for_finalize", "reindex_complete_lock"):
        if docker_ready:
            return "run_finalize.ps1"
        return "wait_docker_and_finalize.ps1"
    return "watch_to_finalize.ps1 -RecordSnapshot"


def build_pipeline_status(
    *,
    artifacts_dir: Path,
    state_path: Path,
    heartbeat_path: Path,
    lock_path: Path,
) -> dict[str, Any]:
    from tmki_ingest.reindex_ops import build_ops_status
    from tmki_runtime.docker_check import docker_daemon_ready

    ops = build_ops_status(
        state_path=state_path,
        heartbeat_path=heartbeat_path,
        lock_path=lock_path,
        artifacts_dir=artifacts_dir,
    )
    docker_ok, docker_detail = docker_daemon_ready()
    report = ops["report"]
    phase = _pipeline_phase(
        ready_for_finalize=bool(ops.get("ready_for_finalize")),
        finalize_done=bool(ops.get("finalize_done")),
        complete=bool(report.get("complete")),
    )
    artifacts = _artifact_flags(artifacts_dir)

    return {
        "phase": phase,
        "ops": ops,
        "docker": {"ready": docker_ok, "detail": docker_detail},
        "artifacts": artifacts,
        "next_step": _next_step(phase=phase, docker_ready=docker_ok),
        "paths": {
            "artifacts_dir": str(artifacts_dir),
        },
    }
