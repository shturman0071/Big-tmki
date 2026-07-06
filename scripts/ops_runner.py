#!/usr/bin/env python3
"""Фоновые задачи, не конкурирующие с Ollama embed (пока идёт индексация).

Запуск:
  python scripts/ops_runner.py
  python scripts/ops_runner.py --task eval-pdf
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ops_registry import upsert_job

PYTHON = sys.executable


def _run(cmd: list[str], *, job_id: str, label: str) -> int:
    upsert_job(job_id, label=label, status="running", progress=0.0, detail="старт")
    try:
        proc = subprocess.run(cmd, cwd=ROOT, check=False)
        status = "done" if proc.returncode == 0 else "failed"
        upsert_job(
            job_id,
            label=label,
            status=status,
            progress=1.0 if status == "done" else None,
            detail=f"exit {proc.returncode}",
        )
        return proc.returncode
    except Exception as exc:
        upsert_job(job_id, label=label, status="failed", detail=str(exc)[:120])
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Параллельные ops без Ollama embed")
    parser.add_argument(
        "--task",
        choices=("all", "eval-pdf", "legal-fetch", "pytest-rag"),
        default="all",
    )
    args = parser.parse_args()
    code = 0

    tasks: list[tuple[str, str, list[str]]] = []
    if args.task in ("all", "eval-pdf"):
        tasks.append(
            (
                "eval-pdf",
                "PoC pdf-oxide",
                [
                    PYTHON,
                    "scripts/eval_pdf_oxide_poc.py",
                    "--limit",
                    "20",
                    "--save",
                    "runtime/artifacts/eval/pdf-oxide-poc.json",
                ],
            )
        )
    if args.task in ("all", "legal-fetch"):
        tasks.append(
            (
                "legal-fetch",
                "Legal corpus fetch",
                [PYTHON, "scripts/legal_corpus_curator.py", "--fetch", "--limit", "5"],
            )
        )
    if args.task in ("all", "pytest-rag"):
        tasks.append(
            (
                "pytest-rag",
                "Тесты RAG (корень)",
                [PYTHON, "-m", "pytest", "tests/test_rag.py", "-q", "--tb=no"],
            )
        )

    upsert_job("ops-runner", label="Ops runner", status="running", detail=f"{len(tasks)} задач")
    for job_id, label, cmd in tasks:
        rc = _run(cmd, job_id=job_id, label=label)
        if rc != 0:
            code = rc
    upsert_job("ops-runner", label="Ops runner", status="done" if code == 0 else "failed")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
