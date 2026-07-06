from pathlib import Path

from tmki_document.reader import format_support_matrix, read_file


def test_read_txt_sample():
    root = Path(__file__).resolve().parents[1]
    sample = root / "artifacts" / "demo-samples" / "sample_markscheider.txt"
    if not sample.is_file():
        return
    row = read_file(sample)
    assert row["readable"] is True
    assert "Маркшейдерская" in row["preview"]


def test_format_support_matrix():
    rows = format_support_matrix()
    exts = {r["extension"] for r in rows}
    assert ".pdf" in exts
    assert ".xlsx" in exts
    assert ".dwg" in exts
    assert ".dxf" in exts
    xlsx_row = next(r for r in rows if r["extension"] == ".xlsx")
    assert xlsx_row["status"] == "read_ingest"
