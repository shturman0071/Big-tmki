from __future__ import annotations

import io
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

from tmki_document.catalog import default_templates_dir, load_template_catalog
from tmki_ingest.document_policy import validate_document_creation_policy

_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")
_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _fill_placeholders(text: str, fields: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return fields.get(key, match.group(0))

    return _PLACEHOLDER_RE.sub(repl, text)


def _write_simple_docx(text: str, out_path: Path) -> None:
    """Минимальный DOCX без внешних зависимостей."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs:
        paragraphs = [""]
    body_parts = []
    for para in paragraphs:
        escaped = (
            para.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        body_parts.append(
            f"<w:p><w:r><w:t xml:space=\"preserve\">{escaped}</w:t></w:r></w:p>"
        )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(body_parts)}<w:sectPr/></w:body></w:document>"
    )
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document_xml)


def create_document_from_template(
    *,
    template_id: str,
    fields: dict[str, str] | None = None,
    policy: dict[str, Any] | None = None,
    output_dir: Path,
    templates_dir: Path | None = None,
    also_docx: bool = True,
) -> dict[str, Any]:
    """
    Создать документ по шаблону TMKI с проверкой document-creation-policy.
    Возвращает пути к файлам и нормализованную policy.
    """
    catalog = load_template_catalog(
        (templates_dir / "catalog.json") if templates_dir else None
    )
    template = catalog["by_id"].get(template_id)
    if not template:
        raise KeyError(f"template_id не найден: {template_id}")

    base = templates_dir or default_templates_dir()
    template_path = base / template["path"]
    if not template_path.is_file():
        raise FileNotFoundError(f"шаблон не найден: {template_path}")

    doc_type = template.get("document_type", "other")
    normalized_policy = validate_document_creation_policy(
        {
            "schema_version": "0.1",
            "document_type": doc_type,
            "use_internal_templates": True,
            "template_id": template_id,
            **(policy or {}),
        }
    )

    today = date.today().isoformat()
    merged_fields = {
        "date": today,
        "author": "TMKI Demo",
        "department": "Маркшейдерское обеспечение",
        "recipient": "Руководитель проекта",
        "title": template.get("title", template_id),
        "body": "Текст по образцу внутреннего документа.",
        **(fields or {}),
    }
    for key in template.get("placeholders", []):
        merged_fields.setdefault(key, "")

    raw = template_path.read_text(encoding="utf-8")
    rendered = _fill_placeholders(raw, merged_fields)

    output_dir.mkdir(parents=True, exist_ok=True)
    doc_id = f"doc_{uuid4().hex[:12]}"
    fmt = template.get("format", "text")
    ext = ".md" if fmt == "markdown" else ".txt"
    out_main = output_dir / f"{doc_id}{ext}"
    out_main.write_text(rendered, encoding="utf-8")

    outputs: dict[str, str] = {"main": str(out_main)}
    if also_docx:
        out_docx = output_dir / f"{doc_id}.docx"
        _write_simple_docx(rendered, out_docx)
        outputs["docx"] = str(out_docx)

    return {
        "doc_id": doc_id,
        "template_id": template_id,
        "template_title": template.get("title"),
        "policy": normalized_policy,
        "fields": merged_fields,
        "outputs": outputs,
    }
