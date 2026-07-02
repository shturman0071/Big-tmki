#!/usr/bin/env python3
"""Проверка Ollama для demo с осмысленными ответами."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def probe_ollama(
    *,
    base_url: str | None = None,
    model: str | None = None,
    timeout: float = 5.0,
) -> dict[str, object]:
    url = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
    mdl = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    out: dict[str, object] = {
        "base_url": url,
        "model": mdl,
        "daemon": False,
        "model_present": False,
        "ready": False,
        "detail": "",
    }
    try:
        req = urllib.request.Request(f"{url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        out["daemon"] = True
        names = [m.get("name", "") for m in data.get("models", [])]
        out["models"] = names
        out["model_present"] = any(n == mdl or n.startswith(f"{mdl}:") for n in names)
        out["ready"] = bool(out["model_present"])
        if not out["model_present"]:
            out["detail"] = f"Модель {mdl} не найдена. Выполните: ollama pull {mdl}"
        else:
            out["detail"] = "ok"
    except urllib.error.URLError as exc:
        out["detail"] = f"Ollama недоступен: {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        out["detail"] = str(exc)
    return out


def resolve_demo_llm(*, prefer: str = "auto") -> str:
    """auto → ollama если готова, иначе stub."""
    if prefer in ("stub", "openai", "ollama"):
        if prefer == "ollama" and not probe_ollama()["ready"]:
            return "stub"
        return prefer
    if probe_ollama()["ready"]:
        return "ollama"
    return "stub"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Ollama for leadership demo")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--resolve", action="store_true", help="Печатать stub|ollama для demo")
    args = parser.parse_args()

    status = probe_ollama()
    if args.resolve:
        print(resolve_demo_llm())
        return 0 if status["ready"] else 1

    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        tag = "ok" if status["ready"] else "warn"
        print(f"Ollama [{tag}]: {status['detail']}")
        if status["daemon"] and not status["model_present"]:
            print(f"  models: {', '.join(status.get('models') or []) or '(пусто)'}")
    return 0 if status["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
