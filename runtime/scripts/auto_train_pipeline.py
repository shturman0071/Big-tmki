#!/usr/bin/env python3
"""
Полный автоматический пайплайн TMKI:
§4 анализ форматов → Azure Q&A → RLM-чанки → датасет → Ollama-модель (+ LoRA если CUDA).

Запуск без участия пользователя:
  cd runtime && python scripts/auto_train_pipeline.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parents[1]
REPO = RUNTIME.parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

ARTIFACTS = RUNTIME / "artifacts" / "training"
DEFAULT_SOURCE = REPO / "data" / "test_docs"

FORMAT_MAP = {
    ".pdf": "format_pdf_analyze",
    ".docx": "format_docx_analyze",
    ".doc": "format_docx_analyze",
    ".xlsx": "format_xlsx_analyze",
    ".xls": "format_xlsx_analyze",
    ".dwg": "format_dwg_analyze",
    ".dxf": "format_dwg_analyze",
    ".tif": "format_pdf_analyze",
    ".tiff": "format_pdf_analyze",
}


def _log(msg: str) -> None:
    print(f"[auto-train] {msg}", flush=True)


def _extract_text(path: Path, max_chars: int = 50000) -> str:
    from tmki_ocr.extractors import extract_local_text, guess_suffix

    raw = path.read_bytes()
    suffix = path.suffix.lower() or guess_suffix(raw, path.name)
    out = extract_local_text(raw, suffix=suffix, source_name=path.name)
    text = (out.get("text") or "").strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n…"
    return text


def _ollama_chat(*, system: str, user: str, model: str) -> str:
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
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return (data.get("message") or {}).get("content", "").strip()


def _collect_files(source: Path) -> list[Path]:
    exts = set(FORMAT_MAP) | {".txt", ".md", ".pptx"}
    if source.is_file():
        return [source]
    files: list[Path] = []
    for ext in exts:
        files.extend(sorted(source.rglob(f"*{ext}")))
    return files


def _load_corrections() -> list[dict[str, Any]]:
    path = RUNTIME / "artifacts" / "demo" / "model-corrections.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("events") or [])
    except (OSError, json.JSONDecodeError):
        return []


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _save_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_pipeline(
    *,
    source: Path,
    model: str,
    num_questions: int = 5,
    limit: int = 0,
    merge_previous: bool = False,
) -> dict[str, Any]:
    from tmki_llm.azure_qa import parse_azure_qa_response, to_chat_samples
    from tmki_llm.rlm import chunk_ctx
    from tmki_runtime.prompt_catalog import load_system_prompt, load_task_prompt, render_task_prompt

    started = time.time()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    state_path = ARTIFACTS / "pipeline-state.json"

    files = _collect_files(source)
    if limit > 0:
        files = files[:limit]

    system_base = load_system_prompt("base")
    rlm_system = load_task_prompt("rlm_system")

    format_reports: list[dict[str, Any]] = []
    qa_rows: list[dict[str, Any]] = []
    chat_samples: list[dict[str, Any]] = []

    if merge_previous:
        qa_rows = _load_jsonl(ARTIFACTS / "qa-pairs.jsonl")
        chat_samples = _load_jsonl(ARTIFACTS / "lora-dataset.jsonl")
        prev_reports = ARTIFACTS / "format-reports.json"
        if prev_reports.is_file():
            try:
                format_reports = json.loads(prev_reports.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                format_reports = []
        _log(f"merge: +{len(qa_rows)} Q&A из предыдущего прогона")

    _log(f"документов: {len(files)} из {source}")

    for doc in files:
        _log(f"обработка: {doc.name}")
        try:
            text = _extract_text(doc)
        except Exception as exc:
            _log(f"  skip extract: {exc}")
            continue
        if not text or len(text) < 80:
            _log("  skip: мало текста")
            continue

        # §4 — анализ формата
        fmt_task = FORMAT_MAP.get(doc.suffix.lower(), "format_pdf_analyze")
        try:
            fmt_prompt = render_task_prompt(fmt_task, context=text[:12000])
            fmt_report = _ollama_chat(system=system_base, user=fmt_prompt, model=model)
        except Exception as exc:
            fmt_report = f"error: {exc}"
        format_reports.append(
            {
                "file": str(doc),
                "format": doc.suffix.lstrip(".").lower(),
                "task": fmt_task,
                "report": fmt_report[:4000],
                "chars": len(text),
            }
        )

        # RLM-чанки (для метаданных датасета)
        chunks = chunk_ctx(text)
        chunk_meta = [{"id": c.chunk_id, "start": c.start, "end": c.end} for c in chunks]

        # Azure Q&A — short + long на каждый документ
        for tpl, qa_type in (
            ("azure_qa_short_answer_ru", "short"),
            ("azure_qa_long_answer_ru", "long"),
        ):
            try:
                user = render_task_prompt(tpl, context=text[:10000], num_questions=str(num_questions))
                raw = _ollama_chat(system=system_base, user=user, model=model)
                pairs = parse_azure_qa_response(raw)
                for pair in pairs:
                    row = {
                        "source_file": str(doc),
                        "qa_type": qa_type,
                        "question": pair["question"],
                        "answer": pair["answer"],
                        "rlm_chunks": len(chunks),
                    }
                    qa_rows.append(row)
                chat_samples.extend(
                    to_chat_samples(
                        pairs,
                        source_file=str(doc),
                        system_prompt=system_base,
                        context=text[:6000],
                    )
                )
                _log(f"  {qa_type}: {len(pairs)} пар")
            except Exception as exc:
                _log(f"  {qa_type} fail: {exc}")

    # Правки пользователя → обучающие пары
    for ev in _load_corrections():
        fb = (ev.get("feedback") or "").strip()
        prev = (ev.get("previous_answer") or "").strip()
        if not fb or len(fb) < 12:
            continue
        import re

        m = re.search(r"(?:неправильно|неверно)\s*[.:,—-]?\s*(.+)$", fb, re.I | re.S)
        correction = (m.group(1).strip() if m else fb)[:2000]
        if not correction:
            continue
        # синтетический вопрос из предыдущего ответа
        question = prev[:300] if prev else "Исправь ответ по документу"
        row = {
            "source_file": ev.get("document_path") or "correction",
            "qa_type": "user_correction",
            "question": question,
            "answer": correction,
            "rlm_chunks": 0,
        }
        qa_rows.append(row)
        chat_samples.extend(
            to_chat_samples(
                [{"question": question, "answer": correction}],
                source_file=row["source_file"],
                system_prompt=system_base,
                context="",
            )
        )

    # Сохранение артефактов
    (ARTIFACTS / "format-reports.json").write_text(
        json.dumps(format_reports, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _save_jsonl(ARTIFACTS / "qa-pairs.jsonl", qa_rows)
    _save_jsonl(ARTIFACTS / "lora-dataset.jsonl", chat_samples)

    state = {
        "started_at": started,
        "finished_at": time.time(),
        "source": str(source),
        "model": model,
        "documents": len(files),
        "format_reports": len(format_reports),
        "qa_pairs": len(qa_rows),
        "chat_samples": len(chat_samples),
        "rlm_system_chars": len(rlm_system),
    }
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _log(f"готово: {state['qa_pairs']} Q&A, {state['chat_samples']} chat samples")
    return state


def create_ollama_model(
    *,
    base_model: str,
    dataset_path: Path,
    model_name: str = "tmki-qwen2.5:7b",
    max_examples: int = 24,
) -> dict[str, Any]:
    """Создать кастомную Ollama-модель с SYSTEM + few-shot из датасета."""
    from tmki_runtime.prompt_catalog import load_system_prompt, load_task_prompt

    if not dataset_path.is_file():
        raise FileNotFoundError(dataset_path)

    system = load_task_prompt("rlm_system") + "\n\n" + load_system_prompt("base")
    examples: list[dict[str, Any]] = []
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        examples.append(json.loads(line))
        if len(examples) >= max_examples:
            break

    modelfile_lines = [
        f"FROM {base_model}",
        'PARAMETER temperature 0.2',
        'PARAMETER num_ctx 8192',
        "",
        'SYSTEM """',
        system.replace('"""', "'''"),
        '"""',
        "",
    ]
    for ex in examples:
        instr = (ex.get("instruction") or "").strip()
        resp = (ex.get("response") or "").strip()
        ctx = (ex.get("context") or "").strip()
        if not instr or not resp:
            continue
        user = f"Контекст:\n{ctx}\n\nВопрос: {instr}" if ctx else instr
        modelfile_lines.append(f'MESSAGE user """{user.replace(chr(34), chr(39))}"""')
        modelfile_lines.append(f'MESSAGE assistant """{resp.replace(chr(34), chr(39))}"""')
        modelfile_lines.append("")

    modelfile_path = ARTIFACTS / "Modelfile"
    modelfile_path.write_text("\n".join(modelfile_lines), encoding="utf-8")

    import subprocess

    _log(f"ollama create {model_name} ...")
    proc = subprocess.run(
        ["ollama", "create", model_name, "-f", str(modelfile_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    result = {
        "model_name": model_name,
        "modelfile": str(modelfile_path),
        "examples_in_modelfile": len(examples),
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-2000:],
        "stderr": (proc.stderr or "")[-2000:],
        "success": proc.returncode == 0,
    }
    (ARTIFACTS / "ollama-create-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if proc.returncode != 0:
        _log(f"ollama create failed: {proc.stderr[:500]}")
    else:
        _log(f"модель создана: {model_name}")
    return result


def try_peft_lora(
    *,
    dataset_path: Path,
    base_model: str = "Qwen/Qwen2.5-7B-Instruct",
    output_dir: Path | None = None,
    max_steps: int = 30,
) -> dict[str, Any]:
    """LoRA через peft (только при CUDA). На CPU пропускается."""
    import torch

    out_dir = output_dir or (ARTIFACTS / "lora-adapter")
    if not torch.cuda.is_available():
        return {"skipped": True, "reason": "no_cuda", "output_dir": str(out_dir)}

    try:
        from datasets import Dataset
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
    except ImportError as exc:
        return {"skipped": True, "reason": f"missing_deps: {exc}"}

    rows: list[dict[str, str]] = []
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        text = ""
        for msg in item.get("messages") or []:
            role = msg.get("role")
            content = msg.get("content") or ""
            if role == "user":
                text += f"<|user|>\n{content}\n"
            elif role == "assistant":
                text += f"<|assistant|>\n{content}\n"
        if text:
            rows.append({"text": text})

    if len(rows) < 3:
        return {"skipped": True, "reason": "too_few_samples", "count": len(rows)}

    ds = Dataset.from_list(rows[:200])
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    lora = LoraConfig(r=8, lora_alpha=16, target_modules=["q_proj", "v_proj"], lora_dropout=0.05, task_type="CAUSAL_LM")
    model = get_peft_model(model, lora)

    def tok(batch):
        return tokenizer(batch["text"], truncation=True, max_length=1024)

    tokenized = ds.map(tok, batched=True, remove_columns=ds.column_names)
    args = TrainingArguments(
        output_dir=str(out_dir),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        max_steps=max_steps,
        learning_rate=2e-4,
        logging_steps=5,
        save_steps=max_steps,
        fp16=True,
        report_to=[],
    )
    trainer = Trainer(model=model, args=args, train_dataset=tokenized)
    trainer.train()
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    return {"skipped": False, "output_dir": str(out_dir), "steps": max_steps, "samples": len(rows)}


def main() -> int:
    import argparse

    from tmki_runtime.rag_env import load_rag_config

    load_rag_config(override=False)

    parser = argparse.ArgumentParser(description="TMKI auto train pipeline")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"))
    parser.add_argument("--base-model", default="qwen2.5:7b", help="Ollama base for create")
    parser.add_argument("--output-model", default="tmki-qwen2.5:7b")
    parser.add_argument("--num-questions", type=int, default=5)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--merge-previous", action="store_true", help="Добавить к существующему датасету")
    parser.add_argument("--max-examples", type=int, default=32, help="Few-shot в Modelfile")
    parser.add_argument("--skip-ollama-create", action="store_true")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        _log(f"source not found: {source}")
        return 1

    state = run_pipeline(
        source=source,
        model=args.model,
        num_questions=args.num_questions,
        limit=args.limit,
        merge_previous=args.merge_previous,
    )

    dataset = ARTIFACTS / "lora-dataset.jsonl"
    ollama_result: dict[str, Any] = {"skipped": True}
    if not args.skip_ollama_create and dataset.is_file():
        ollama_result = create_ollama_model(
            base_model=args.base_model,
            dataset_path=dataset,
            model_name=args.output_model,
            max_examples=args.max_examples,
        )

    lora_result = try_peft_lora(dataset_path=dataset)

    summary = {
        "pipeline": state,
        "ollama": ollama_result,
        "peft_lora": lora_result,
        "use_model": args.output_model if ollama_result.get("success") else args.model,
        "artifacts_dir": str(ARTIFACTS),
    }
    (ARTIFACTS / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _log(f"summary -> {ARTIFACTS / 'summary.json'}")
    _log(f"используйте модель: {summary['use_model']}")
    return 0 if state.get("qa_pairs", 0) > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
