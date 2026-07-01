from tmki_ingest.reindex_errors_lib import error_key, load_error_audit, summarize_errors


def test_error_key():
    assert error_key("KeyError: 'skip_temp'") == "KeyError"
    assert error_key("") == "unknown"


def test_summarize_errors():
    rows = [
        {"path": "a.pdf", "error": "KeyError: x"},
        {"path": "b.pdf", "error": "KeyError: y"},
        {"path": "c.pdf", "error": "TimeoutError"},
    ]
    out = summarize_errors(rows)
    assert out["recent_count"] == 3
    assert out["summary"][0]["type"] == "KeyError"
    assert out["summary"][0]["count"] == 2


def test_load_error_audit():
    state = {
        "stats": {"errors": 5},
        "recent_errors": [{"path": "x", "error": "OSError: disk"}],
    }
    audit = load_error_audit(state)
    assert audit["errors_total"] == 5
    assert audit["recent_count"] == 1
