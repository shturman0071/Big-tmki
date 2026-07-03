from tmki_ocr.ocr import HttpMinerUProvider, HttpMistralOcrProvider, run_ocr


def test_http_mineru_provider(monkeypatch):
    monkeypatch.setenv("TMKI_OCR_MODE", "http")

    def mock_post(url, payload, headers, timeout):
        assert "file_base64" in payload
        return {
            "markdown": "Маркшейдерская съёмка из HTTP MinerU",
            "page_count": 1,
            "avg_confidence": 0.91,
        }

    provider = HttpMinerUProvider(api_url="http://mineru.test/ocr", http_post=mock_post)
    result = run_ocr(
        doc_id="doc_http",
        trace_id="00000000-0000-4000-8000-000000000096",
        raw_bytes=b"%PDF-test",
        mineru_provider=provider,
        mistral_provider=HttpMistralOcrProvider(
            api_url="http://mistral.test/ocr",
            http_post=lambda *a, **k: {"markdown": "fallback"},
        ),
    )
    assert result["ocr_status"] == "completed"
    assert result["provider_used"] == "mineru"
    assert "HTTP MinerU" in result["_markdown"]


def test_http_mistral_fallback(monkeypatch):
    def mineru_fail(url, payload, headers, timeout):
        return {"markdown": "", "page_count": 0, "avg_confidence": 0.0}

    def mistral_ok(url, payload, headers, timeout):
        assert payload.get("model") == "mistral-ocr-latest"
        assert payload["document"]["type"] == "document_url"
        return {
            "pages": [{"markdown": "Fallback HTTP Mistral OCR текст маркшейдерская съёмка"}],
        }

    mineru = HttpMinerUProvider(api_url="http://mineru.test/ocr", http_post=mineru_fail)
    mistral = HttpMistralOcrProvider(api_url="http://mistral.test/ocr", http_post=mistral_ok)
    result = run_ocr(
        doc_id="doc_fb_http",
        trace_id="00000000-0000-4000-8000-000000000095",
        raw_bytes=b"%PDF",
        mineru_provider=mineru,
        mistral_provider=mistral,
    )
    assert result["fallback_used"] is True
    assert result["provider_used"] == "mistral_ocr_4"
    assert "Mistral" in result["_markdown"]
