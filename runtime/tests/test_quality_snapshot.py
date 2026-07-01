from tmki_ingest.quality_snapshot import augment_quality_payload


def test_augment_quality_payload():
    report = {"percent": 73.0, "live_progress": 7300, "total": 10000, "chunks_v2": 7000}
    payload = {"v2_count": 7000, "rows": []}
    out = augment_quality_payload(payload, report)
    assert out["snapshot_kind"] == "partial_reindex"
    assert out["reindex_percent"] == 73.0
    assert out["v2_count"] == 7000
