"""Тесты онлайн-eval Q→A по ground-truth."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from tmki_demo.qa_eval import (
    _citation_match,
    get_eval_snapshot,
    load_suite,
    reset_eval,
    run_one,
)

ROOT = Path(__file__).resolve().parents[2]
GROUND = ROOT / "data" / "ground_truth"


def test_load_skru2_suite():
    tests = load_suite("skru-2")
    assert len(tests) >= 10
    assert tests[0]["id"].startswith("skru_")


def test_citation_match_needles():
    test = {
        "expect_any_in_citation": ["копр", "клетьев"],
        "expect_path_contains": "клетьев",
    }
    ok, _ = _citation_match(
        [{"file_name": "акт копра.docx", "relative_path": "КС/клетьевый/акт.docx", "snippet": "проверка"}],
        test,
    )
    assert ok


def test_citation_match_fails_without_citations():
    test = {"expect_any_in_citation": ["копр"]}
    ok, reason = _citation_match([], test)
    assert not ok
    assert "цитат" in reason


def test_reset_and_run_one_mocked(tmp_path, monkeypatch):
    state_path = tmp_path / "qa-eval-state.json"
    failures_path = tmp_path / "qa-eval-failures.json"
    monkeypatch.setattr("tmki_demo.qa_eval.STATE_PATH", state_path)
    monkeypatch.setattr("tmki_demo.qa_eval.FAILURES_PATH", failures_path)

    reset_eval(corpus_id="skru-2")
    snap = get_eval_snapshot()
    assert snap["cursor"] == 0
    assert snap["total"] >= 1

    fake = {
        "answer": "тест",
        "citations": [
            {
                "file_name": "акт копра клетьевого ствола.docx",
                "relative_path": "маркшейдерия/КС/клетьев/акт.docx",
                "snippet": "копр",
            }
        ],
    }
    with patch("tmki_demo.qa.ask_regulations", return_value=fake):
        result = run_one(corpus_id="skru-2", llm="stub")

    assert result["cursor"] == 1
    assert result["passed"] >= 1
    assert result["transcript"][-1]["role"] == "answer"


def test_ground_truth_file_valid():
    path = GROUND / "skru2_qa.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["corpus_id"] == "skru-2"
    for t in data["tests"]:
        assert t.get("question")
        assert t.get("id")
