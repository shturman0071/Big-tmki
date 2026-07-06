#!/usr/bin/env python3
"""PoC: сравнение извлечения текста из PDF (pypdf vs docling vs pdf-oxide CLI).

Запуск (после установки pdf-oxide, если есть):
  python scripts/eval_pdf_oxide_poc.py --limit 20
  python scripts/eval_pdf_oxide_poc.py --save runtime/artifacts/eval/pdf-oxide-poc.json

Решение go/no-go — в `18_technology_watch.md` (Watchlist pdf-oxide).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
sys.path.insert(0, str(RUNTIME))

DEFAULT_ARCHIVE = Path(os.environ.get("TMKI_REGULATIONS_ARCHIVE", r"D:\Курсор\СКРУ-2"))
OUT_DIR = RUNTIME / "artifacts" / "eval"


def _pypdf_text(path: Path) -> tuple[str, float]:
    t0 = time.time()
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages[:30]:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip(), time.time() - t0
    except Exception as exc:
        return f"ERROR: {exc}", time.time() - t0


def _docling_text(path: Path) -> tuple[str, float]:
    t0 = time.time()
    try:
        from tmki_ocr.parser_backend import _try_docling

        raw = path.read_bytes()
        parsed = _try_docling(raw, suffix=path.suffix)
        if parsed:
            return (parsed.get("text") or "").strip(), time.time() - t0
        return "", time.time() - t0
    except Exception as exc:
        return f"ERROR: {exc}", time.time() - t0


def _pdf_oxide_text(path: Path, *, cmd: str) -> tuple[str, float]:
    t0 = time.time()
    if not shutil.which(cmd.split()[0]) and not Path(cmd.split()[0]).is_file():
        return "SKIP: pdf-oxide CLI not installed", 0.0
    try:
        proc = subprocess.run(
            [*cmd.split(), str(path)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        out = (proc.stdout or proc.stderr or "").strip()
        return out, time.time() - t0
    except Exception as exc:
        return f"ERROR: {exc}", time.time() - t0


def _sample_pdfs(archive: Path, limit: int, seed: int) -> list[Path]:
    pdfs = list(archive.rglob("*.pdf"))
    if not pdfs:
        return []
    rng = random.Random(seed)
    rng.shuffle(pdfs)
    return pdfs[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="PoC pdf-oxide vs pypdf vs docling")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--pdf-oxide-cmd",
        default=os.environ.get("TMKI_PDF_OXIDE_CMD", "pdf-oxide"),
        help="CLI для pdf-oxide (если установлен)",
    )
    parser.add_argument("--save", type=Path, default=None)
    args = parser.parse_args()

    if not args.archive.is_dir():
        print(f"Архив не найден: {args.archive}", file=sys.stderr)
        return 1

    files = _sample_pdfs(args.archive, args.limit, args.seed)
    if not files:
        print("PDF не найдены", file=sys.stderr)
        return 1

    rows: list[dict] = []
    for path in files:
        rel = str(path.relative_to(args.archive))
        pypdf_txt, pypdf_sec = _pypdf_text(path)
        doc_txt, doc_sec = _docling_text(path)
        ox_txt, ox_sec = _pdf_oxide_text(path, cmd=args.pdf_oxide_cmd)
        rows.append(
            {
                "path": rel,
                "chars": {
                    "pypdf": len(pypdf_txt),
                    "docling": len(doc_txt),
                    "pdf_oxide": len(ox_txt) if not ox_txt.startswith("SKIP") else 0,
                },
                "seconds": {"pypdf": round(pypdf_sec, 3), "docling": round(doc_sec, 3), "pdf_oxide": round(ox_sec, 3)},
                "pdf_oxide_status": "skip" if ox_txt.startswith("SKIP") else "ok",
            }
        )
        print(
            f"{rel[:60]:60}  pypdf={len(pypdf_txt):5}  docling={len(doc_txt):5}  oxide={rows[-1]['chars']['pdf_oxide']:5}"
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "archive": str(args.archive),
        "sample_size": len(rows),
        "pdf_oxide_cmd": args.pdf_oxide_cmd,
        "rows": rows,
        "summary": {
            "avg_chars_pypdf": round(sum(r["chars"]["pypdf"] for r in rows) / len(rows), 1),
            "avg_chars_docling": round(sum(r["chars"]["docling"] for r in rows) / len(rows), 1),
        },
    }
    oxide_ok = [r for r in rows if r["pdf_oxide_status"] == "ok"]
    if oxide_ok:
        report["summary"]["avg_chars_pdf_oxide"] = round(
            sum(r["chars"]["pdf_oxide"] for r in oxide_ok) / len(oxide_ok), 1
        )

    out = args.save or OUT_DIR / "pdf-oxide-poc.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nОтчёт: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
