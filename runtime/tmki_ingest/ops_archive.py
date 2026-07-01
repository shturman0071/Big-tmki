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
        "paths": {
            "archive": str(archive_path),
            "artifacts_dir": str(artifacts_dir),
        },
    }
