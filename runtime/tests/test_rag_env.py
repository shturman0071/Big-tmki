from tmki_runtime.rag_env import apply_aliases, parse_env_file, repo_root


def test_rag_env_aliases():
    import os

    apply_aliases(
        {
            "OLLAMA_URL": "http://localhost:11434",
            "TMKI_EMBEDDING_DIM": "768",
            "TMKI_RERANK_ENABLED": "1",
            "TMKI_RERANK_MODEL": "cross-encoder/test",
        },
        override=True,
    )
    assert os.environ["OLLAMA_BASE_URL"] == "http://localhost:11434"
    assert os.environ["TMKI_EMBEDDING_DIMS"] == "768"
    assert os.environ["TMKI_CROSS_ENCODER_RERANK"] == "1"
    assert os.environ["TMKI_CROSS_ENCODER_MODEL"] == "cross-encoder/test"


def test_rag_config_example_parseable():
    example = repo_root() / "config" / "rag_config.env.example"
    values = parse_env_file(example)
    assert values["TMKI_INDEX_BACKEND"] == "pgvector"
    assert values["TMKI_PGVECTOR_TABLE"] == "chunks"
    assert values["TMKI_EMBEDDING_DIMS"] == "768"
