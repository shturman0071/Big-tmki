from tmki_ingest.reindex_stats import build_ingest_stats


def test_build_ingest_stats_yield():
    state = {"stats": {"imported": 90, "skip_temp": 5, "too_large": 2, "errors": 3, "ocr_failed": 0}}
    report = {"live_progress": 100, "total": 200, "processed": 95, "chunks_v2": 90}
    stats = build_ingest_stats(state, report)
    assert stats["import_yield_pct"] == 90.0
    assert stats["pending_scan"] == 100
    assert stats["skip_temp"] == 5
