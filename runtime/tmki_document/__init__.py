"""Создание документов по внутренним шаблонам TMKI (v0.3 demo)."""

from tmki_document.author import create_document_from_template
from tmki_document.catalog import default_templates_dir, load_template_catalog
from tmki_document.reader import format_support_matrix, read_file

__all__ = [
    "create_document_from_template",
    "default_templates_dir",
    "format_support_matrix",
    "load_template_catalog",
    "read_file",
]
