"""Загрузка config/rag_config.env из корня репозитория и алиасы env-переменных."""

from __future__ import annotations

import os
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG = _REPO_ROOT / "config" / "rag_config.env"

# Корневые имена → runtime-конвенции
_ALIASES: dict[str, str] = {
    "OLLAMA_URL": "OLLAMA_BASE_URL",
    "OLLAMA_LLM_MODEL": "OLLAMA_MODEL",
    "TMKI_EMBEDDING_DIM": "TMKI_EMBEDDING_DIMS",
    "TMKI_RERANK_ENABLED": "TMKI_CROSS_ENCODER_RERANK",
    "TMKI_RERANK_MODEL": "TMKI_CROSS_ENCODER_MODEL",
    "TMKI_RERANK_TOP_K": "TMKI_RAG_FINAL_K",
}


def repo_root() -> Path:
    return _REPO_ROOT


def _strip_inline_comment(value: str) -> str:
    if "#" not in value:
        return value.strip()
    return re.split(r"\s+#", value, maxsplit=1)[0].strip()


def parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_inline_comment(value.strip().strip('"').strip("'"))
        if key:
            out[key] = value
    return out


def apply_aliases(values: dict[str, str], *, override: bool = False) -> None:
    for key, value in values.items():
        if override or not os.environ.get(key):
            os.environ[key] = value
        alias = _ALIASES.get(key)
        if alias and (override or not os.environ.get(alias)):
            os.environ[alias] = value


def load_rag_config(
    path: Path | None = None,
    *,
    override: bool = False,
) -> dict[str, str]:
    """
    Загрузить config/rag_config.env.
    override=False — не перезаписывать уже заданные переменные окружения.
    """
    config_path = path or _DEFAULT_CONFIG
    values = parse_env_file(config_path)
    if values:
        apply_aliases(values, override=override)
    return values


def reconcile_rag_config_after_secrets() -> None:
    """После runtime/.env: приоритет у config/rag_config.env для БД и индекса."""
    values = parse_env_file(_DEFAULT_CONFIG)
    priority = (
        "DATABASE_URL",
        "TMKI_INDEX_BACKEND",
        "TMKI_PGVECTOR_TABLE",
        "TMKI_EMBEDDING_PROVIDER",
        "TMKI_EMBEDDING_MODEL",
        "TMKI_EMBEDDING_DIM",
        "TMKI_EMBEDDING_DIMS",
        "OLLAMA_URL",
        "OLLAMA_BASE_URL",
        "OLLAMA_EMBEDDING_MODEL",
        "OLLAMA_MODEL",
        "TMKI_SYSTEM_PROMPT_PATH",
    )
    subset = {k: values[k] for k in priority if k in values}
    if subset:
        apply_aliases(subset, override=True)


def resolve_system_prompt_path() -> Path | None:
    raw = os.environ.get("TMKI_SYSTEM_PROMPT_PATH", "").strip()
    if not raw:
        return None
    candidate = Path(raw)
    if candidate.is_file():
        return candidate
    from_repo = _REPO_ROOT / raw
    if from_repo.is_file():
        return from_repo
    return None
