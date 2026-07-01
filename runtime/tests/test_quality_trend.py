import json
from pathlib import Path

from tmki_ingest.quality_trend import load_partial_quality_files, summarize_quality_trend


def test_summarize_quality_trend(tmp_path: Path):
    a = tmp_path / "quality-partial-p50.json"
    b = tmp_path / "quality-partial-p70.json"
    a.write_text(
        json.dumps(
            {
                "reindex_percent": 50.0,
                "v2_count": 100,
                "rows": [{"hits": 3, "avg_score": 0.5}],
            }
        ),
        encoding="utf-8",
    )
    b.write_text(
        json.dumps(
            {
                "reindex_percent": 70.0,
                "v2_count": 200,
                "rows": [{"hits": 3, "avg_score": 0.7}],
            }
        ),
        encoding="utf-8",
    )
    snaps = load_partial_quality_files(tmp_path)
    trend = summarize_quality_trend(snaps)
    assert trend["count"] == 2
    assert trend["points"][0]["percent"] == 50.0
    assert trend["points"][1]["avg_score"] == 0.7
