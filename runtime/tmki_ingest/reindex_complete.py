"""Снимок готовности re-index к finalize (100%)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_reindex_complete_snapshot(
    *,
    artifacts_dir: Path,
    state_path: Path,
    heartbeat_path: Path,
    lock_path: Path,
    dsn: str | None = None,
) -> dict[str, Any]:
    from tmki_ingest.handoff_summary import format_handoff
    from tmki_ingest.ops_bundle import build_ops_bundle
    from tmki_ingest.preflight_finalize import build_preflight_finalize

    ops_bundle = build_ops_bundle(
        artifacts_dir=artifacts_dir,
        state_path=state_path,
        heartbeat_path=heartbeat_path,
        lock_path=lock_path,
    )
    preflight = build_preflight_finalize(
        state_path=state_path,
        heartbeat_path=heartbeat_path,
        lock_path=lock_path,
        dsn=dsn,
    )
    handoff_text = format_handoff(ops_bundle)
    snapshot_path = artifacts_dir / "reindex-complete-latest.json"
    handoff_path = artifacts_dir / "reindex-handoff.txt"

    return {
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "kind": "reindex_complete",
        "preflight": preflight,
        "ops_bundle": ops_bundle,
        "handoff_text": handoff_text,
        "paths": {
            "snapshot": str(snapshot_path),
            "handoff": str(handoff_path),
            "ops_bundle": str(artifacts_dir / "reindex-ops-bundle-latest.json"),
        },
    }
