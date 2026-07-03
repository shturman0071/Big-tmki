"""Автоопределение опциональных фич: parser, pgvector, fusion-llm, rerank."""

from __future__ import annotations

import importlib.util
import os
from typing import Any

DEFAULT_PG_DSN = "postgresql://tmki:tmki_dev@127.0.0.1:5432/tmki"

AUTO_MANAGED_KEYS = frozenset(
    {
        "TMKI_INGEST_PARSER",
        "TMKI_RAG_FUSION_LLM",
        "TMKI_INDEX_BACKEND",
        "DATABASE_URL",
        "TMKI_CROSS_ENCODER_RERANK",
    }
)


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def detect_ingest_parser() -> str:
    if _module_available("docling"):
        return "docling"
    if _module_available("kreuzberg") or _module_available("xberg"):
        return "kreuzberg"
    return "default"


def detect_fusion_llm() -> str:
    import json
    import urllib.error
    import urllib.request

    url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    try:
        req = urllib.request.Request(f"{url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        names = [m.get("name", "") for m in data.get("models", [])]
        ready = any(n == model or n.startswith(f"{model}:") for n in names)
        return "1" if ready else "0"
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return "0"


def detect_cross_encoder_rerank() -> str:
    try:
        from tmki_rag.cross_encoder import available

        return "1" if available() else "0"
    except Exception:
        return "0"


def _pgvector_ready(dsn: str) -> tuple[bool, int]:
    try:
        import psycopg
    except ImportError:
        return False, 0
    try:
        with psycopg.connect(dsn, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_name = 'tmki_chunks'"
                )
                if cur.fetchone()[0] == 0:
                    return False, 0
                cur.execute("SELECT COUNT(*) FROM tmki_chunks")
                row = cur.fetchone()
                n = int(row[0]) if row else 0
                return n > 0, n
    except Exception:
        return False, 0


def detect_pgvector(*, dsn: str | None = None) -> dict[str, str]:
    """Вернуть DATABASE_URL + TMKI_INDEX_BACKEND если БД доступна и не пуста."""
    candidates: list[str] = []
    if dsn:
        candidates.append(dsn)
    env_dsn = os.environ.get("DATABASE_URL", "").strip()
    if env_dsn and env_dsn not in candidates:
        candidates.append(env_dsn)
    if DEFAULT_PG_DSN not in candidates:
        candidates.append(DEFAULT_PG_DSN)

    for url in candidates:
        ok, rows = _pgvector_ready(url)
        if ok:
            return {"DATABASE_URL": url, "TMKI_INDEX_BACKEND": "pgvector"}
    return {"TMKI_INDEX_BACKEND": "json"}


def _is_auto(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().lower() in ("", "auto", "detect")


def autoconfigure(
    current: dict[str, str],
    *,
    locked_keys: set[str] | None = None,
) -> tuple[dict[str, str], list[str]]:
    """
    Дополнить env автоопределёнными значениями.
    locked_keys — ключи из secrets.local: не перезаписывать.
    Возвращает (updates, log_lines).
    """
    locked = locked_keys or set()
    updates: dict[str, str] = {}
    log: list[str] = []

    if os.environ.get("TMKI_AUTO_CONFIGURE", "1").strip().lower() in ("0", "false", "no"):
        return updates, ["AUTO:disabled"]

    parser_key = "TMKI_INGEST_PARSER"
    if parser_key not in locked and _is_auto(current.get(parser_key)):
        val = detect_ingest_parser()
        updates[parser_key] = val
        log.append(f"AUTO:{parser_key}={val}")

    fusion_key = "TMKI_RAG_FUSION_LLM"
    if fusion_key not in locked and _is_auto(current.get(fusion_key)):
        val = detect_fusion_llm()
        updates[fusion_key] = val
        log.append(f"AUTO:{fusion_key}={val}")

    rerank_key = "TMKI_CROSS_ENCODER_RERANK"
    if rerank_key not in locked and _is_auto(current.get(rerank_key)):
        val = detect_cross_encoder_rerank()
        updates[rerank_key] = val
        if val == "0":
            log.append(f"AUTO:{rerank_key}=0 (sentence-transformers not installed)")

    backend_key = "TMKI_INDEX_BACKEND"
    dsn_key = "DATABASE_URL"
    if backend_key not in locked and _is_auto(current.get(backend_key)):
        pg = detect_pgvector(dsn=current.get(dsn_key) if dsn_key not in locked else None)
        updates.update(pg)
        if pg.get(backend_key) == "pgvector":
            log.append(f"AUTO:{backend_key}=pgvector rows>0")
        else:
            log.append(f"AUTO:{backend_key}=json")

    return updates, log


def apply_autoconfigure_to_secrets(
    secrets_path: Any,
    *,
    locked_keys: set[str],
) -> list[str]:
    """Дописать в secrets.local авто-ключи, которых там ещё нет."""
    from pathlib import Path

    path = Path(secrets_path)
    current: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            current[k.strip()] = v.strip()

    updates, log = autoconfigure(current, locked_keys=locked_keys)
    to_add = {k: v for k, v in updates.items() if k not in current}
    if not to_add:
        return log

    block = ["", "# --- auto-detected (merge_env.py) ---"]
    for k in sorted(to_add):
        block.append(f"{k}={to_add[k]}")
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(block) + "\n")
    log.append(f"AUTO:appended {len(to_add)} key(s) to secrets.local")
    return log
