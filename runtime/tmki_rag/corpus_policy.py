"""Политика корпусов: какой LLM допустим для какого архива (egress control)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CLOUD_LLM = frozenset({"openai", "anthropic"})
LOCAL_LLM = frozenset({"stub", "ollama"})


@dataclass(frozen=True)
class CorpusProfile:
    corpus_id: str
    label: str
    archive_env: str
    default_archive: Path
    artifacts_dir: str
    cloud_llm_only: bool
    local_llm_only: bool


CORPORA: dict[str, CorpusProfile] = {
    "test_docs": CorpusProfile(
        corpus_id="test_docs",
        label="Test docs (demo)",
        archive_env="TMKI_TEST_DOCS_DIR",
        default_archive=Path(__file__).resolve().parents[2] / "data" / "test_docs",
        artifacts_dir="regulations-import",
        cloud_llm_only=False,
        local_llm_only=True,
    ),
    "skru-2": CorpusProfile(
        corpus_id="skru-2",
        label="СКРУ-2",
        archive_env="TMKI_REGULATIONS_ARCHIVE",
        default_archive=Path(r"D:\Курсор\СКРУ-2"),
        artifacts_dir="regulations-import",
        cloud_llm_only=False,
        local_llm_only=True,
    ),
    "arm-ks": CorpusProfile(
        corpus_id="arm-ks",
        label="Армировка КС",
        archive_env="TMKI_ARM_KS_ARCHIVE",
        default_archive=Path(r"D:\Курсор\Армировка КС"),
        artifacts_dir="arm-ks-import",
        cloud_llm_only=True,
        local_llm_only=False,
    ),
    "vks": CorpusProfile(
        corpus_id="vks",
        label="ВКС",
        archive_env="TMKI_VKS_ARCHIVE",
        default_archive=Path(r"D:\Курсор\ВКС"),
        artifacts_dir="vks-import",
        cloud_llm_only=False,
        local_llm_only=True,
    ),
}

_CORPUS_ALIASES: dict[str, str] = {
    "test_docs": "test_docs",
    "test-docs": "test_docs",
    "скру2": "skru-2",
    "skru-2": "skru-2",
    "skru2": "skru-2",
    "arm-ks": "arm-ks",
    "armks": "arm-ks",
    "армировка кс": "arm-ks",
    "армировка-кс": "arm-ks",
    "армировка_кс": "arm-ks",
    "vks": "vks",
    "вкс": "vks",
}


def normalize_corpus_id(value: str | None) -> str:
    if not value:
        env = os.environ.get("TMKI_DEFAULT_CORPUS", "").strip()
        if env:
            return normalize_corpus_id(env)
        return "skru-2"
    key = value.strip().lower().replace("\\", "/")
    if key in _CORPUS_ALIASES:
        return _CORPUS_ALIASES[key]
    if key in CORPORA:
        return key
    return "skru-2"


def get_corpus(corpus_id: str | None = None) -> CorpusProfile:
    return CORPORA[normalize_corpus_id(corpus_id)]


def resolve_corpus_archive(corpus_id: str | None = None) -> Path:
    profile = get_corpus(corpus_id)
    env = os.environ.get(profile.archive_env, "").strip()
    if env:
        return Path(env)
    return profile.default_archive


def resolve_corpus_artifacts_dir(corpus_id: str | None = None) -> Path:
    profile = get_corpus(corpus_id)
    base = Path(__file__).resolve().parents[1] / "artifacts"
    override = os.environ.get("TMKI_ARTIFACTS_DIR")
    if override:
        base = Path(override)
    return base / profile.artifacts_dir


def detect_corpus_from_path(path: str | Path) -> str | None:
    target = Path(str(path)).resolve()
    for profile in CORPORA.values():
        root = resolve_corpus_archive(profile.corpus_id).resolve()
        try:
            target.relative_to(root)
            return profile.corpus_id
        except ValueError:
            continue
    lowered = str(target).lower()
    if "скру-2" in lowered or "скру2" in lowered:
        return "skru-2"
    if "армировка" in lowered and "кс" in lowered:
        return "arm-ks"
    if "вкс" in lowered:
        return "vks"
    return None


def _fallback_local() -> str:
    if os.environ.get("OLLAMA_BASE_URL") or os.environ.get("TMKI_LLM_PROVIDER") == "ollama":
        return "ollama"
    return "stub"


from tmki_runtime.secrets import is_valid_openai_api_key


def _ollama_ready() -> bool:
    try:
        import importlib.util
        from pathlib import Path

        script = Path(__file__).resolve().parents[1] / "scripts" / "check_ollama.py"
        spec = importlib.util.spec_from_file_location("check_ollama", script)
        if not spec or not spec.loader:
            return False
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return bool(mod.probe_ollama()["ready"])
    except Exception:
        return False


def _fallback_cloud() -> str:
    prefer = os.environ.get("TMKI_LLM_PROVIDER", "").lower()
    if prefer == "ollama" and _ollama_ready():
        return "ollama"
    if is_valid_openai_api_key(os.environ.get("OPENAI_API_KEY")) and prefer != "ollama":
        return "openai"
    if _ollama_ready():
        return "ollama"
    return "stub"


def enforce_llm_for_corpus(
    provider: str,
    corpus_id: str | None,
    *,
    explicit: bool = False,
) -> tuple[str, str | None]:
    """
    Привести provider к политике корпуса.
    Возвращает (provider, policy_note).
    """
    profile = get_corpus(corpus_id)
    name = (provider or "stub").lower()
    if profile.local_llm_only and name in CLOUD_LLM:
        fallback = _fallback_local()
        note = f"Облачная LLM запрещена для «{profile.label}» — используется {fallback}."
        return fallback, note
    if profile.cloud_llm_only and name in LOCAL_LLM and not explicit:
        if (
            is_valid_openai_api_key(os.environ.get("OPENAI_API_KEY"))
            and os.environ.get("TMKI_LLM_PROVIDER", "").lower() != "ollama"
        ):
            return "openai", f"Для «{profile.label}» разрешена облачная LLM (openai)."
        fallback = _fallback_cloud()
        return fallback, f"OpenAI отложен/недоступен — для «{profile.label}» используется {fallback}."
    if profile.cloud_llm_only and name in LOCAL_LLM and explicit:
        return name, f"Явно выбран {name}, но для «{profile.label}» рекомендуется openai."
    return name, None


def enforce_llm_for_paths(
    provider: str,
    paths: list[str | Path],
) -> tuple[str, str | None]:
    """Блокировать облако, если среди путей есть документы из локального-only корпуса."""
    corpora = {detect_corpus_from_path(p) for p in paths if p}
    corpora.discard(None)
    if "skru-2" in corpora and (provider or "").lower() in CLOUD_LLM:
        fallback = _fallback_local()
        return fallback, "Облачная LLM отменена: в контексте есть документы из СКРУ-2."
    if corpora == {"arm-ks"} and (provider or "").lower() in LOCAL_LLM:
        if is_valid_openai_api_key(os.environ.get("OPENAI_API_KEY")):
            return "openai", "Для документов «Армировка КС» используется облачная LLM."
    return (provider or "stub").lower(), None


def corpus_policy_snapshot() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for profile in CORPORA.values():
        root = resolve_corpus_archive(profile.corpus_id)
        out.append(
            {
                "corpus_id": profile.corpus_id,
                "label": profile.label,
                "archive_root": str(root),
                "archive_exists": root.is_dir(),
                "llm_mode": "cloud_only" if profile.cloud_llm_only else "local_only",
                "allowed_llm": (
                    ["openai", "ollama", "stub"]
                    if profile.cloud_llm_only
                    else ["stub", "ollama"]
                ),
            }
        )
    return out
