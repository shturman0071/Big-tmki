from tmki_ocr.ocr import run_ocr

__all__ = ["run_ocr"]


def test_run_ocr_mineru_ok():
    raw = b"%PDF-1.4 test"
    result = run_ocr(doc_id="doc_test", trace_id="00000000-0000-4000-8000-000000000099", raw_bytes=raw)
    assert result["ocr_status"] == "completed"
    assert result["provider_used"] == "mineru"
    assert result["fallback_used"] is False
    assert result["extracted_char_count"] > 0


def test_run_ocr_fallback_low_confidence():
    result = run_ocr(
        doc_id="doc_fb",
        trace_id="00000000-0000-4000-8000-000000000098",
        raw_bytes=b"%PDF",
        mineru_mode="low_confidence",
    )
    assert result["fallback_used"] is True
    assert result["provider_used"] == "mistral_ocr_4"
    assert result["fallback_reason"] == "low_confidence"


def test_run_ocr_fallback_primary_error():
    result = run_ocr(
        doc_id="doc_err",
        trace_id="00000000-0000-4000-8000-000000000097",
        raw_bytes=b"x",
        mineru_mode="error",
    )
    assert result["fallback_used"] is True
    assert result["provider_used"] == "mistral_ocr_4"
    assert result["fallback_reason"] == "primary_error"


def test_http_mineru_provider_mock(monkeypatch):
    monkeypatch.setenv("TMKI_OCR_MODE", "http")

    def fake_post(url: str, payload: dict, headers: dict, timeout: int) -> dict:
        return {"markdown": "HTTP MinerU text", "avg_confidence": 0.91}

    from tmki_ocr.ocr import HttpMinerUProvider, run_ocr

    result = run_ocr(
        doc_id="doc_http",
        trace_id="t-http",
        raw_bytes=b"%PDF",
        mineru_provider=HttpMinerUProvider(api_url="http://test/mineru", http_post=fake_post),
        mistral_provider=HttpMinerUProvider(api_url="http://test/m", http_post=fake_post),
    )
    assert result["ocr_status"] == "completed"
    assert result["provider_used"] == "mineru"
