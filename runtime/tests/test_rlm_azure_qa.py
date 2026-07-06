"""Тесты Azure Q&A и RLM."""

from tmki_llm.azure_qa import parse_azure_qa_response, to_chat_samples
from tmki_llm.rlm import chunk_ctx


def test_parse_azure_qa():
    raw = """
[Q]: Когда подписан акт?
[A]: 24 января 2024
[Q]: Кто председатель комиссии?
[A]: Зубцов А.М.
"""
    pairs = parse_azure_qa_response(raw)
    assert len(pairs) == 2
    assert pairs[0]["question"].startswith("Когда")


def test_to_chat_samples():
    samples = to_chat_samples(
        [{"question": "Q?", "answer": "A."}],
        system_prompt="sys",
        context="ctx",
    )
    assert len(samples) == 1
    assert samples[0]["messages"][-1]["content"] == "A."


def test_chunk_ctx():
    text = "а" * 5000
    chunks = chunk_ctx(text, chunk_size=2000, overlap=100)
    assert len(chunks) >= 2
    assert chunks[0].chunk_id == 0
