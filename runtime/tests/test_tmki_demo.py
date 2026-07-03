from unittest.mock import MagicMock, patch

from tmki_demo.qa import ask_regulations, resolve_document, resolve_llm_provider


def test_resolve_llm_provider_env():
    with patch.dict("os.environ", {"TMKI_LLM_PROVIDER": "stub"}, clear=False):
        assert resolve_llm_provider() == "stub"


def test_ask_regulations_stub():
    fake_output = {
        "answer": "Тестовый ответ",
        "confidence": "high",
        "citations": [{"doc_id": "doc_x", "snippet": "фрагмент"}],
        "llm_provider": "stub",
        "loop_state": "loop_complete",
    }
    mock_index = MagicMock()
    mock_index.count.return_value = 10
    with patch("tmki_demo.qa._answer_open_intent", return_value=None):
        with patch("tmki_demo.qa._get_catalog") as catalog_get:
            catalog_get.return_value.enrich_citations.side_effect = lambda items: items
            catalog_get.return_value.search_paths.return_value = []
            with patch("tmki_demo.qa._resolve_backend", return_value=("json", mock_index, [])):
                with patch("tmki_demo.qa._run_content_search", return_value=fake_output):
                    result = ask_regulations("тест", llm_provider="stub")
    assert result["answer"] == "Тестовый ответ"
    assert result["citations"][0]["doc_id"] == "doc_x"
    assert result["backend"] == "json"


def test_ask_regulations_open_intent():
    mock_index = MagicMock()
    mock_index.count.return_value = 10
    open_payload = {
        "answer": "Нашёл файлы",
        "confidence": "high",
        "citations": [{"file_name": "a.pdf", "absolute_path": "C:/a.pdf", "relative_path": "a.pdf"}],
        "intent": "open",
        "matched_files": [],
    }
    with patch("tmki_rag.doc_catalog.DocCatalog.load") as catalog_cls:
        catalog_cls.return_value.search_paths.return_value = []
        with patch("tmki_demo.qa._answer_open_intent", return_value=open_payload):
            with patch("tmki_demo.qa._resolve_backend", return_value=("json", mock_index, [])):
                result = ask_regulations("открой a.pdf", llm_provider="stub")
    assert result["intent"] == "open"
    assert "Нашёл" in result["answer"]


def test_ask_regulations_fast_filename_lookup():
    mock_index = MagicMock()
    mock_index.count.return_value = 10
    fast_payload = {
        "answer": "Нашёл файлы",
        "confidence": "high",
        "citations": [{"file_name": "z.docx", "absolute_path": "C:/z.docx", "relative_path": "z.docx"}],
        "intent": "file",
        "matched_files": [],
    }
    with patch("tmki_demo.qa._answer_open_intent", return_value=None):
        with patch("tmki_demo.qa._fast_file_lookup", return_value=fast_payload):
            with patch("tmki_demo.qa._resolve_backend", return_value=("json", mock_index, [])):
                result = ask_regulations("Замечания_КМД_КС18105", llm_provider="stub", corpus_id="arm-ks")
    assert result["intent"] == "file"
    assert result["citations"][0]["file_name"] == "z.docx"


def test_resolve_document_query():
    with patch("tmki_demo.qa._get_catalog") as catalog_get:
        catalog_get.return_value.search_paths.return_value = [{"file_name": "x.pdf"}]
        out = resolve_document(query="x.pdf")
    assert out["status"] == "ok"
    assert out["matches"][0]["file_name"] == "x.pdf"

