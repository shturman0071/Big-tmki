import json
from pathlib import Path

from tmki_ingest.finalize_report import build_post_finalize_report


def test_build_post_finalize_report(tmp_path: Path):
    audit = {
        "report": {"live_progress": 100, "total": 100, "chunks_v2": 99},
        "errors": {"errors_total": 2},
    }
    quality = {"v1_count": 10, "v2_count": 99, "rows": []}
    (tmp_path / "reindex-audit-latest.json").write_text(json.dumps(audit), encoding="utf-8")
    (tmp_path / "quality-benchmark-final.json").write_text(json.dumps(quality), encoding="utf-8")

    report = build_post_finalize_report(tmp_path, dsn="")
    assert report["reindex"]["chunks_v2"] == 99
    assert report["errors_total"] == 2
    assert report["quality_benchmark"]["v2_count"] == 99
    assert report["pgvector_rows"] is None
