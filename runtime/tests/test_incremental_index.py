from tmki_rag.index import ChunkIndex


def test_remove_by_source_path():
    idx = ChunkIndex(
        [
            {"chunk_id": "1", "source_relative_path": "a/one.pdf", "content_preview": "x"},
            {"chunk_id": "2", "source_relative_path": "b/two.pdf", "content_preview": "y"},
            {"chunk_id": "3", "source_relative_path": "a/one.pdf", "content_preview": "z"},
        ]
    )
    removed = idx.remove_by_source_path("a/one.pdf")
    assert removed == 2
    assert len(idx.list()) == 1
    assert idx.list()[0]["chunk_id"] == "2"
