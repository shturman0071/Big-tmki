"""Тесты каталога промптов."""

from tmki_runtime.prompt_catalog import (
    list_prompts,
    load_system_prompt,
    load_task_prompt,
    render_task_prompt,
    task_placeholders,
)


def test_catalog_lists_tasks():
    names = list_prompts()
    assert "analyze_structure" in names["tasks"]
    assert "base" in names["system"]


def test_system_prompt_base():
    text = load_system_prompt("base")
    assert "TMKI" in text
    assert "ТОЛЬКО на основе" in text


def test_render_task_prompt():
    rendered = render_task_prompt("qa_generate_basic_user", context="тестовый документ")
    assert "тестовый документ" in rendered


def test_task_placeholders():
    ph = task_placeholders("eval_completeness")
    assert "context" in ph
    assert "question" in ph
    assert "answer" in ph


def test_all_task_files_load():
    for name in list_prompts()["tasks"]:
        text = load_task_prompt(name)
        assert len(text) >= 10, name
