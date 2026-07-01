import json
from pathlib import Path

from tmki_ingest.ops_archive import build_ops_archive


def test_build_ops_archive(tmp_path: Path):
    state = {
        "processed": ["a"] * 10,
        "total_candidates": 10,
        "stats": {"imported": 9, "errors": 0, "skip_temp": 0, "too_large": 0},
        "updated_at": "2026-01-01T00:00:00Z",
    }
    state_path = tmp_path / "reindex-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    hb = tmp_path / "reindex-heartbeat.json"
    hb.write_text(json.dumps({"file_index": 10}), encoding="utf-8")
    (tmp_path / "chunks-v2.json").write_text(json.dumps({"chunks": [{"id": "c1"}]}), encoding="utf-8")
    (tmp_path / "reindex-handoff.txt").write_text("TMKI re-index handoff", encoding="utf-8")

    archive = build_ops_archive(
        artifacts_dir=tmp_path,
        state_path=state_path,
        heartbeat_path=hb,
        lock_path=tmp_path / "nolock",
    )
    assert archive["kind"] == "ops_archive"
    assert archive["pipeline"]["phase"] == "ready_for_finalize"
    assert archive["handoff_reindex"].startswith("TMKI re-index handoff")
    assert archive["paths"]["archive"].endswith("tmki-ops-archive-latest.json")
