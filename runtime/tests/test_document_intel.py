"""Тесты Document Intelligence: память, ранжирование, парсинг анализа."""

from __future__ import annotations

from pathlib import Path

from tmki_rag.document_intel import (
    DocumentMemoryStore,
    DocumentProfile,
    detect_analyze_intent,
    parse_analysis_text,
    rank_file_matches_for_content_query,
)
from tmki_rag.retrieval import detect_query_intent


def test_detect_analyze_intent():
    assert detect_analyze_intent("проанализируй письмо 452")
    assert detect_query_intent("выдели главное в акте") == "analyze"
    assert detect_query_intent("кратко опиши письмо") == "summarize"


def test_parse_analysis_text():
    raw = (
        "СУТЬ: Письмо о правках КМД по объекту 452.\n"
        "ГЛАВНОЕ:\n"
        "- заменить узел ограждения\n"
        "- согласовать с Проминвест\n"
        "ТИП: письмо"
    )
    parsed = parse_analysis_text(raw)
    assert "452" in parsed.gist or "КМД" in parsed.gist
    assert len(parsed.key_points) == 2
    assert parsed.doc_type == "письмо"


def test_rank_prefers_letter_over_remarks():
    matches = [
        {"relative_path": "Замечания_КМД_452.pdf", "file_name": "Замечания_КМД_452.pdf", "score": 5.0},
        {"relative_path": "452 правки письма.pdf", "file_name": "452 правки письма.pdf", "score": 4.0},
    ]
    ranked = rank_file_matches_for_content_query(
        "опиши текст письма 452",
        matches,
        prefer_letters=True,
    )
    assert "письма" in ranked[0]["file_name"].lower()


def test_document_memory_store_roundtrip(tmp_path: Path):
    store = DocumentMemoryStore(tmp_path / "doc-profiles.json")
    profile = DocumentProfile(
        doc_id="doc_abc",
        relative_path="a/letter.pdf",
        gist="Тестовая суть",
        key_points=["пункт 1"],
        doc_type="письмо",
        content_fingerprint="sha256:deadbeef",
        analyzed_at="2026-07-03T12:00:00+00:00",
        llm_provider="stub",
        corpus_id="arm-ks",
    )
    store.put(profile)
    reloaded = DocumentMemoryStore(tmp_path / "doc-profiles.json")
    got = reloaded.get("doc_abc")
    assert got is not None
    assert got.gist == "Тестовая суть"
    assert got.key_points == ["пункт 1"]
