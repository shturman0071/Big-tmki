from tmki_ingest.handoff_summary import format_handoff


def test_format_handoff_basic():
    bundle = {
        "dashboard": {
            "ops": {
                "report": {"live_progress": 8000, "total": 10089, "percent": 79.3},
                "ingest_stats": {"imported": 7500, "chunks_v2": 7489, "import_yield_pct": 96.0, "skip_temp": 60, "too_large": 8},
                "errors": {"errors_total": 39},
            },
            "eta": {"from_state_hours": 0.5},
        },
        "partial_quality_trend": {"points": [{"percent": 70.0, "v2_count": 6000, "avg_score": 0.65}]},
        "paths": {"ops_bundle": "/tmp/bundle.json"},
    }
    text = format_handoff(bundle)
    assert "79.3%" in text
    assert "Partial quality trend" in text
    assert "Ready for finalize" not in text
