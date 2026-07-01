"""Сборка post-finalize ops bundle."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_finalize_ops_bundle(artifacts_dir: Path, *, dsn: str | None = None) -> dict[str, Any]:
    from tmki_ingest.finalize_report import build_post_finalize_report
    from tmki_ingest.handoff_summary import format_finalize_handoff

    report = build_post_finalize_report(artifacts_dir, dsn=dsn)
    handoff_path = artifacts_dir / "finalize-handoff.txt"
    if handoff_path.is_file():
        handoff_text = handoff_path.read_text(encoding="utf-8").strip()
    else:
        handoff_text = format_finalize_handoff(report)

    def _read(name: str) -> dict[str, Any] | None:
        p = artifacts_dir / name
        if not p.is_file():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    bundle_path = artifacts_dir / "finalize-ops-bundle-latest.json"
    return {
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "kind": "finalize_ops_bundle",
        "finalize_report": report,
        "handoff_text": handoff_text,
        "quality_benchmark": _read("quality-benchmark-final.json"),
        "reindex_ops_bundle": _read("reindex-ops-bundle-latest.json"),
        "finalize_marker": _read("finalize-done.json"),
        "paths": {
            "artifacts_dir": str(artifacts_dir),
            "finalize_summary": str(artifacts_dir / "finalize-summary-latest.json"),
            "finalize_handoff": str(handoff_path),
            "finalize_ops_bundle": str(bundle_path),
            "quality_benchmark": str(artifacts_dir / "quality-benchmark-final.json"),
        },
    }
