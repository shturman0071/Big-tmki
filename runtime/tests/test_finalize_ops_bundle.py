import json
from pathlib import Path

from tmki_ingest.finalize_ops_bundle import build_finalize_ops_bundle


def test_build_finalize_ops_bundle(tmp_path: Path):
    audit = {
        "report": {"live_progress": 100, "total": 100, "chunks_v2": 99},
        "errors": {"errors_total": 2},
    }
    quality = {"v1_count": 10, "v2_count": 99, "rows": []}
    summary = {
        "reindex": {"live_progress": 100, "total": 100, "chunks_v2": 99},
        "errors_total": 2,
        "quality_benchmark": quality,
        "artifacts": {"summary": str(tmp_path / "finalize-summary-latest.json")},
    }
    (tmp_path / "reindex-audit-latest.json").write_text(json.dumps(audit), encoding="utf-8")
    (tmp_path / "quality-benchmark-final.json").write_text(json.dumps(quality), encoding="utf-8")
    (tmp_path / "finalize-summary-latest.json").write_text(json.dumps(summary), encoding="utf-8")
    (tmp_path / "finalize-handoff.txt").write_text("TMKI finalize handoff\n", encoding="utf-8")

    bundle = build_finalize_ops_bundle(tmp_path, dsn="")
    assert bundle["kind"] == "finalize_ops_bundle"
    assert bundle["handoff_text"].startswith("TMKI finalize handoff")
    assert bundle["finalize_report"]["quality_benchmark"]["v2_count"] == 99
    assert bundle["paths"]["finalize_ops_bundle"].endswith("finalize-ops-bundle-latest.json")
