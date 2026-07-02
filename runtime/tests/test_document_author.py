from pathlib import Path

from tmki_document.author import create_document_from_template
from tmki_document.catalog import load_template_catalog


def test_load_template_catalog():
    cat = load_template_catalog()
    assert "instruction_internal" in cat["by_id"]
    assert "memo_internal" in cat["by_id"]


def test_create_document_from_template(tmp_path: Path):
    result = create_document_from_template(
        template_id="instruction_internal",
        fields={
            "title": "Тест",
            "author": "Demo",
            "department": "MS",
            "body": "Пункт 1.",
        },
        output_dir=tmp_path,
    )
    assert result["policy"]["external_law_check"] == "never"
    main = Path(result["outputs"]["main"])
    docx = Path(result["outputs"]["docx"])
    assert main.is_file()
    assert docx.is_file()
    text = main.read_text(encoding="utf-8")
    assert "Тест" in text
    assert "Пункт 1." in text
    assert "{{" not in text
