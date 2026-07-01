from datetime import date
from pathlib import Path

from tmki_llm.providers import LlmGenerateResult
from tmki_policy import build_policy_context, load_org_snapshot
from tmki_rag import VectorChunkIndex
from tmki_runtime import run_mvp
from tmki_runtime.mvp import load_chunks

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "schemas/org/examples/satimol-snapshot.example.json"
CHUNKS = ROOT / "schemas/document/examples/satimol-chunks.example.json"


def test_mvp_with_vector_index_and_ollama(monkeypatch):
    class FakeOllama:
        def generate(self, *, query, citations, read_only_mode=False):
            return LlmGenerateResult(
                answer="Ответ Ollama по маркшейдерской съёмке.",
                confidence="high",
                citations=citations,
                provider="ollama",
                model="qwen2.5:7b",
            )

    monkeypatch.setenv("TMKI_LLM_PROVIDER", "ollama")
    monkeypatch.setattr("tmki_runtime.mvp.get_llm_provider", lambda: FakeOllama())

    snapshot = load_org_snapshot(SNAPSHOT)
    ctx = build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )
    index = VectorChunkIndex()
    index.add(load_chunks(CHUNKS))

    result = run_mvp(
        message="маркшейдерская съёмка на участке КС",
        policy_context=ctx,
        chunks=[],
        index=index,
        use_hybrid_search=True,
        llm_provider="ollama",
        trace_id="00000000-0000-4000-8000-000000000050",
        run_id="00000000-0000-4000-8000-000000000051",
    )

    assert result["loop_state"]["loop_state"] == "loop_complete"
    assert result["output"]["llm_provider"] == "ollama"
    assert "Ollama" in result["output"]["answer"]
    assert len(result["output"]["citations"]) >= 1
