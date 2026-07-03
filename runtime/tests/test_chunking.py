from tmki_ingest.chunking import build_chunks_from_ocr, split_text_windows


def test_split_text_windows_single_short():
    windows = split_text_windows("короткий текст")
    assert len(windows) == 1
    assert windows[0][2] == "короткий текст"


def test_split_text_windows_multiple():
    text = "а" * 2500
    windows = split_text_windows(text, chunk_size=1000, overlap=200)
    assert len(windows) >= 2
    assert all(len(w[2]) <= 1000 for w in windows)


def test_build_chunks_from_ocr_multi():
    long_text = ("Требования ростехнадзора к кранам. " * 80).strip()
    chunks = build_chunks_from_ocr(
        {"doc_id": "doc_test123"},
        company_id="co",
        project_id="pr",
        department_id=None,
        folder_id=None,
        classification="internal",
        markdown=long_text,
    )
    assert len(chunks) >= 2
    assert chunks[0]["chunk_id"].endswith("_01")
    assert chunks[1]["chunk_id"].endswith("_02")
    combined = "".join(c["content_preview"] for c in chunks)
    assert "ростехнадзора" in combined
