"""Master ops archive: pipeline + snapshots + handoff."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip()


def build_ops_archive(
    *,
    artifacts_dir: Path,
    state_path: Path,
    heartbeat_path: Path,
    lock_path: Path,
) -> dict[str, Any]:
    from tmki_ingest.pipeline_status import build_pipeline_status

    pipeline = build_pipeline_status(
        artifacts_dir=artifacts_dir,
        state_path=state_path,
        heartbeat_path=heartbeat_path,
        lock_path=lock_path,
    )
    archive_path = artifacts_dir / "tmki-ops-archive-latest.json"
    return {
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "kind": "ops_archive",
        "pipeline": pipeline,
        "reindex_complete": _read_json(artifacts_dir / "reindex-complete-latest.json"),
        "reindex_ops_bundle": _read_json(artifacts_dir / "reindex-ops-bundle-latest.json"),
        "finalize_summary": _read_json(artifacts_dir / "finalize-summary-latest.json"),
        "finalize_ops_bundle": _read_json(artifacts_dir / "finalize-ops-bundle-latest.json"),
        "handoff_reindex": _read_text(artifacts_dir / "reindex-handoff.txt"),
        "handoff_finalize": _read_text(artifacts_dir / "finalize-handoff.txt"),
        "reindex_audit": _read_json(artifacts_dir / "reindex-audit-latest.json"),
        "paths": {
            "archive": str(archive_path),
            "artifacts_dir": str(artifacts_dir),
        },
    }


def format_ops_archive_summary(archive: dict[str, Any]) -> str:
    lines = ["TMKI ops archive summary", ""]
    pipeline = archive.get("pipeline") or {}
    ops = pipeline.get("ops") or {}
    r = ops.get("report") or {}
    lines.append(f"Phase: {pipeline.get('phase')}")
    if r:
        lines.append(f"Progress: {r.get('live_progress')}/{r.get('total')} ({r.get('percent')}%)")
        lines.append(f"chunks_v2: {r.get('chunks_v2')}")
    docker = pipeline.get("docker") or {}
    lines.append(f"Docker: {'ok' if docker.get('ready') else 'not ready'}")
    err = (ops.get("errors") or {}).get("errors_total")
    if err is not None:
        lines.append(f"Errors: {err}")
    audit = archive.get("reindex_audit") or {}
    err_summary = (audit.get("errors") or {}).get("summary") or []
    if err_summary:
        top = ", ".join(f"{row['type']}={row['count']}" for row in err_summary[:5])
        lines.append(f"Error types: {top}")

    arts = [k for k, v in (pipeline.get("artifacts") or {}).items() if v]
    if arts:
        lines.append(f"Artifacts: {', '.join(arts)}")

    if pipeline.get("next_step"):
        lines.append("")
        lines.append(f"Next: .\\scripts\\{pipeline['next_step']}")

    archive_path = (archive.get("paths") or {}).get("archive")
    if archive_path:
        lines.append("")
        lines.append(f"Archive: {archive_path}")

    return "\n".join(lines)
