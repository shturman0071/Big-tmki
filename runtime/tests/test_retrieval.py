from pathlib import Path

from tmki_rag.doc_catalog import DocCatalog, doc_id_from_bytes
from tmki_rag.retrieval import (
    chunk_text_quality,
    detect_query_intent,
    looks_like_content_summary_query,
    looks_like_filename_query,
    normalize_query,
    rerank_results,
)


def test_detect_open_intent():
    assert detect_query_intent("открой акт маркшейдерской") == "open"
    assert detect_query_intent("кран ростехнадзор") == "qa"


def test_detect_summarize_intent():
    assert detect_query_intent("кратко опиши текст письма Проминвест") == "summarize"
    assert looks_like_content_summary_query("о чем письмо от Балыко")
    assert detect_query_intent("найди ТТН и опиши содержание") == "summarize"


def test_looks_like_filename_query():
    assert looks_like_filename_query("Замечания_КМД_КС18105_05.11.21_1")
    assert looks_like_filename_query("ПРИ 50314-18105-КМД")
    assert not looks_like_filename_query("кран ростехнадзор")


def test_normalize_query():
    assert "ростехнадзор" in normalize_query("кран ростех надзор").lower()
    assert "опасный производственный объект" in normalize_query("ОПО требования").lower()
    assert "пожарная безопасность" in normalize_query("инструкция по пожарной безопасности").lower()
    assert "Ог-1" in normalize_query("замечания ограждение 1")


def test_chunk_text_quality_filters_noise():
    assert chunk_text_quality("12.345 67.890 12.345 67.890") < 0.2
    assert chunk_text_quality("Акт приема-передачи маркшейдерской опорной сети участка") > 0.5


def test_rerank_prefers_meaningful_text():
    results = [
        {
            "doc_id": "d1",
            "score": 0.9,
            "citation": {"snippet": "12.34 56.78 90.12 34.56", "doc_id": "d1"},
        },
        {
            "doc_id": "d2",
            "score": 0.7,
            "citation": {
                "snippet": "Требования ростехнадзора к подъемным сооружениям и кранам на ОПО",
                "doc_id": "d2",
            },
        },
    ]
    ranked = rerank_results("кран ростехнадзор", results, top_k=2)
    assert ranked[0]["doc_id"] == "d2"


def test_doc_catalog_search_paths(tmp_path: Path):
    archive = tmp_path / "archive"
    (archive / "Маркшейдерия").mkdir(parents=True)
    target = archive / "Маркшейдерия" / "акт опорной сети.pdf"
    target.write_bytes(b"pdf-demo")
    catalog = DocCatalog(archive_root=archive, cache_path=tmp_path / "doc-catalog.json")
    matches = catalog.search_paths("акт опорной сети", limit=5)
    assert matches
    assert matches[0]["file_name"] == "акт опорной сети.pdf"


def test_doc_id_from_bytes_stable():
    raw = b"same-content"
    assert doc_id_from_bytes(raw) == doc_id_from_bytes(raw)


def test_doc_catalog_resolve_doc_id(tmp_path: Path):
    archive = tmp_path / "archive"
    archive.mkdir()
    file_path = archive / "reglament.pdf"
    content = b"reglament-body"
    file_path.write_bytes(content)
    catalog = DocCatalog(archive_root=archive, cache_path=tmp_path / "doc-catalog.json")
    doc_id = doc_id_from_bytes(content)
    catalog.register_mapping(doc_id, "reglament.pdf")
    catalog._save_cache()
    resolved = catalog.resolve_doc_id(doc_id, max_new_hashes=10)
    assert resolved is not None
    assert resolved["file_name"] == "reglament.pdf"
