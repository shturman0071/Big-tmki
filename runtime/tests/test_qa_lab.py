"""Тесты QA-лаборатории форматов."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from tmki_demo.qa_lab import (
    get_files_list,
    load_format_suite,
    record_verdict,
    reset_lab,
    resolve_archive_file,
    select_item,
)

ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "data" / "ground_truth" / "skru2_format_lab.json"


def test_format_suite_exists():
    assert SUITE.is_file()
    tests = load_format_suite()
    assert len(tests) >= 20
    formats = {t["format"] for t in tests}
    assert "pdf" in formats
    assert "docx" in formats


def test_resolve_archive_file_under_root():
    tests = load_format_suite()
    if not tests:
        return
    rel = tests[0]["document_relative_path"]
    path = resolve_archive_file(corpus_id="skru-2", relative_path=rel)
    assert path is not None
    assert path.is_file()


def test_resolve_rejects_traversal():
    assert resolve_archive_file(corpus_id="skru-2", relative_path="../secrets.txt") is None


def test_files_list_has_twenty():
    snap = get_files_list()
    assert snap["total"] == 20
    assert len(snap.get("suite_list") or []) == 20
    formats = {x["format"] for x in snap["suite_list"]}
    assert len(formats) >= 15


def test_select_item(tmp_path, monkeypatch):
    state_path = tmp_path / "qa-lab-state.json"
    verdicts_path = tmp_path / "qa-lab-verdicts.json"
    monkeypatch.setattr("tmki_demo.qa_lab.STATE_PATH", state_path)
    monkeypatch.setattr("tmki_demo.qa_lab.VERDICTS_PATH", verdicts_path)

    reset_lab(corpus_id="skru-2")
    snap = select_item(index=2)
    assert snap["cursor"] == 2
    assert snap["current"]["id"] == snap["suite_list"][2]["id"]
    assert snap["suite_list"][2]["status"] == "current"


def test_reset_and_verdict_flow(tmp_path, monkeypatch):
    state_path = tmp_path / "qa-lab-state.json"
    verdicts_path = tmp_path / "qa-lab-verdicts.json"
    monkeypatch.setattr("tmki_demo.qa_lab.STATE_PATH", state_path)
    monkeypatch.setattr("tmki_demo.qa_lab.VERDICTS_PATH", verdicts_path)

    snap = reset_lab(corpus_id="skru-2")
    assert snap["total"] >= 1
    assert snap["current"] is not None
    assert len(snap.get("suite_list") or []) >= 1

    out = record_verdict(verdict="ok", note="")
    assert out["cursor"] == 1
    assert out["stats"]["ok"] == 1


def test_ground_truth_schema():
    data = json.loads(SUITE.read_text(encoding="utf-8"))
    assert data["corpus_id"] == "skru-2"
    for t in data["tests"]:
        assert t.get("document_relative_path")
        assert t.get("format")
        assert t.get("question")
