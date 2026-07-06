"""Каталог промптов TMKI (prompts/catalog.json + prompts/tasks/*.txt)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CATALOG_PATH = _REPO_ROOT / "prompts" / "catalog.json"
_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


@lru_cache(maxsize=1)
def _catalog() -> dict[str, Any]:
    if not _CATALOG_PATH.is_file():
        return {"system": {}, "tasks": {}}
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def repo_root() -> Path:
    return _REPO_ROOT


def list_prompts() -> dict[str, Any]:
    """Список system- и task-промптов из каталога."""
    cat = _catalog()
    return {
        "system": list((cat.get("system") or {}).keys()),
        "tasks": list((cat.get("tasks") or {}).keys()),
    }


def _resolve_path(rel_path: str) -> Path:
    candidate = Path(rel_path)
    if candidate.is_file():
        return candidate
    from_repo = _REPO_ROOT / rel_path
    if from_repo.is_file():
        return from_repo
    raise FileNotFoundError(f"prompt file not found: {rel_path}")


def load_system_prompt(name: str = "base") -> str:
    """base | extended"""
    entry = (_catalog().get("system") or {}).get(name)
    if not entry:
        raise KeyError(f"unknown system prompt: {name}")
    return _resolve_path(entry["path"]).read_text(encoding="utf-8").strip()


def load_task_prompt(name: str) -> str:
    entry = (_catalog().get("tasks") or {}).get(name)
    if not entry:
        raise KeyError(f"unknown task prompt: {name}")
    return _resolve_path(entry["path"]).read_text(encoding="utf-8").strip()


def render_prompt(template: str, **variables: str) -> str:
    """Подстановка {{placeholder}} в шаблоне."""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in variables:
            raise KeyError(f"missing placeholder: {key}")
        return variables[key]

    return _PLACEHOLDER.sub(repl, template).strip()


def render_task_prompt(name: str, **variables: str) -> str:
    return render_prompt(load_task_prompt(name), **variables)


def task_placeholders(name: str) -> list[str]:
    entry = (_catalog().get("tasks") or {}).get(name) or {}
    return list(entry.get("placeholders") or [])
