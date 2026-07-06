#!/usr/bin/env python3
"""Генерация Q&A-пар из документов по шаблонам prompts/tasks/."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from tmki_runtime.prompt_catalog import load_system_prompt, load_task_prompt, render_task_prompt


def _extract_text(path: Path, max_chars: int) -> str:
    from tmki_ocr.extractors import extract_local_text, guess_suffix

    raw = path.read_bytes()
    suffix = path.suffix.lower() or guess_suffix(raw, path.name)
    out = extract_local_text(raw, suffix=suffix, source_name=path.name)
    text = (out.get("text") or "").strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n…"
    return text


def _call_ollama(*, system: str, user: str, model: str) -> str:
    import urllib.error
    import urllib.request

    base = os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OLLAMA_URL") or "http://127.0.0.1:11434"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }
    req = urllib.request.Request(
        f"{base.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return (data.get("message") or {}).get("content", "").strip()


def _parse_json_array(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    start = text.find("[")
    end = text.rfind("]")
    if start < 0 or end < 0:
        raise ValueError("response is not a JSON array")
    return json.loads(text[start : end + 1])


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Q&A pairs from documents")
    parser.add_argument("--source", required=True, help="File or directory")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument(
        "--template",
        default="qa_generate_basic",
        choices=["qa_generate_basic", "qa_generate_typed", "qa_generate_multihop"],
    )
    parser.add_argument("--max-chars", type=int, default=12000)
    parser.add_argument("--limit", type=int, default=0, help="Max files (0 = all)")
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"))
    args = parser.parse_args()

    from tmki_runtime.rag_env import load_rag_config

    load_rag_config(override=False)

    source = Path(args.source)
    files: list[Path] = []
    if source.is_file():
        files = [source]
    elif source.is_dir():
        for ext in (".pdf", ".docx", ".doc", ".txt", ".md", ".xlsx", ".pptx"):
            files.extend(sorted(source.rglob(f"*{ext}")))
    else:
        print(f"source not found: {source}", file=sys.stderr)
        return 1

    if args.limit > 0:
        files = files[: args.limit]

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.template == "qa_generate_basic":
        system = load_task_prompt("qa_generate_basic_system")
        user_tpl = "qa_generate_basic_user"
    else:
        system = load_system_prompt("base")
        user_tpl = args.template

    written = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for doc in files:
            try:
                context = _extract_text(doc, args.max_chars)
            except Exception as exc:
                print(f"skip {doc}: {exc}", file=sys.stderr)
                continue
            if not context:
                continue
            user = render_task_prompt(user_tpl, context=context)
            try:
                raw = _call_ollama(system=system, user=user, model=args.model)
                pairs = _parse_json_array(raw)
            except Exception as exc:
                print(f"fail {doc}: {exc}", file=sys.stderr)
                continue
            for pair in pairs:
                row = {
                    "source_file": str(doc),
                    "template": args.template,
                    **pair,
                }
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                written += 1
            print(f"ok {doc.name}: {len(pairs)} pairs")

    print(f"written {written} rows -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
