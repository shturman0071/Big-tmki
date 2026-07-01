import json
from pathlib import Path

from tmki_ingest.post_finalize_verify import build_post_finalize_verify


def test_build_post_finalize_verify_ok(tmp_path: Path):
    audit = {"report": {"live_progress": 100, "total": 100, "chunks_v2": 99}, "errors": {"errors_total": 1}}
    quality = {"v1_count": 10, "v2_count": 99}
    summary = {
        "reindex": {"chunks_v2": 99},
        "quality_benchmark": quality,
        "pgvector_rows": 99,
    }
    (tmp_path / "finalize-done.json").write_text("{}", encoding="utf-8")
    (tmp_path / "finalize-summary-latest.json").write_text(json.dumps(summary), encoding="utf-8")
    (tmp_path / "finalize-handoff.txt").write_text("handoff", encoding="utf-8")
    (tmp_path / "finalize-ops-bundle-latest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "quality-benchmark-final.json").write_text(json.dumps(quality), encoding="utf-8")
    (tmp_path / "reindex-audit-latest.json").write_text(json.dumps(audit), encoding="utf-8")

    out = build_post_finalize_verify(tmp_path, dsn="")
    assert out["verified"] is True
    assert any(c["name"] == "finalize_done" and c["ok"] for c in out["checks"])
