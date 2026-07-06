"""Тесты голосового стенда по документу."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from tmki_demo.doc_voice import (
    get_session_snapshot,
    list_documents,
    open_document,
    process_turn,
    synthesize_tts_payload,
)


def test_list_documents_empty_query():
    with patch("tmki_demo.doc_voice._catalog") as mock_cat:
        inst = mock_cat.return_value
        inst.paths = ["a/1.pdf", "b/2.docx"]
        inst.archive_root = Path("D:/x")
        inst.search_paths.return_value = []
        out = list_documents(corpus_id="skru-2", query="", limit=5)
        assert out["total"] == 2
        assert out["items"][0]["file_name"] == "1.pdf"


def test_open_and_turn_flow(tmp_path, monkeypatch):
    monkeypatch.setattr("tmki_demo.doc_voice.SESSIONS_DIR", tmp_path)
    with patch("tmki_demo.doc_voice._enrich_doc") as enrich:
        enrich.return_value = {
            "corpus_id": "skru-2",
            "relative_path": "t/a.pdf",
            "file_name": "a.pdf",
            "absolute_path": "D:/t/a.pdf",
            "format": "pdf",
            "exists": True,
            "view_mode": "embed",
        }
        with patch("tmki_demo.doc_voice.synthesize_tts_payload", return_value={"provider": "stub"}):
            snap = open_document(corpus_id="skru-2", relative_path="t/a.pdf", llm="stub")
        sid = snap["session_id"]
        assert sid
        assert snap["document"]["file_name"] == "a.pdf"

    with patch("tmki_demo.doc_voice._doc_citations", return_value=[{"snippet": "текст", "file_name": "a.pdf"}]):
        with patch("tmki_demo.doc_voice._answer_voice_question", return_value="ответ по документу"):
            with patch("tmki_demo.doc_voice.synthesize_tts_payload", return_value={"provider": "stub"}):
                out = process_turn(session_id=sid, kind="user_question", text="что в документе?", llm="stub")
        assert "ответ по документу" in out["assistant_text"]

    with patch("tmki_demo.doc_voice._llm_text", return_value="Какой номер акта?"):
        with patch("tmki_demo.doc_voice.synthesize_tts_payload", return_value={"provider": "stub"}):
            quiz = process_turn(session_id=sid, kind="ai_quiz", llm="stub")
        assert quiz["pending_ai_question"]

    state = get_session_snapshot(sid)
    assert len(state["turns"]) >= 3


def test_user_feedback_turn(tmp_path, monkeypatch):
    monkeypatch.setattr("tmki_demo.doc_voice.SESSIONS_DIR", tmp_path)
    with patch("tmki_demo.doc_voice._enrich_doc") as enrich:
        enrich.return_value = {
            "corpus_id": "skru-2",
            "relative_path": "t/a.pdf",
            "file_name": "a.pdf",
            "absolute_path": "D:/t/a.pdf",
            "format": "pdf",
            "exists": True,
            "view_mode": "embed",
        }
        with patch("tmki_demo.doc_voice.synthesize_tts_payload", return_value={"provider": "stub"}):
            snap = open_document(corpus_id="skru-2", relative_path="t/a.pdf", llm="stub")
        sid = snap["session_id"]

    with patch("tmki_demo.doc_voice._doc_citations", return_value=[]):
        with patch("tmki_voice.model_learn.record_model_feedback", return_value={"feedback": "нет"}):
            with patch("tmki_demo.doc_voice.synthesize_tts_payload", return_value={"provider": "stub"}):
                out = process_turn(
                    session_id=sid,
                    kind="user_feedback",
                    text="Неправильно. Главный механик Цененко В.Д.",
                    llm="stub",
                )
    assert "Цененко" in out["assistant_text"]
    assert out.get("feedback_recorded")


def test_parse_user_correction():
    from tmki_demo.doc_voice import _parse_user_correction

    assert _parse_user_correction("Неправильно. Главный механик Цененко В.Д.") == "Главный механик Цененко В.Д"
    assert _parse_user_correction("Правильно: номер 453") == "номер 453"


def test_answer_voice_question_without_citations():
    from tmki_demo.doc_voice import _NO_ANSWER, _answer_voice_question

    with patch("tmki_demo.doc_voice._voice_citations_for_question", return_value=[]):
        assert _answer_voice_question(
            question="какой номер?",
            corpus_id="skru-2",
            relative_path="a.pdf",
            llm="stub",
        ) == _NO_ANSWER


def test_synthesize_tts_stub():
    out = synthesize_tts_payload("привет")
    assert "provider" in out
