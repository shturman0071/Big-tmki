#!/usr/bin/env python3
"""Re-index регламентов с локальным извлечением текста (TMKI_OCR_MODE=local)."""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARCHIVE = Path(r"D:\Курсор\ТМКИ оригнал")
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import"


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-index regulations with local text extraction")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--checkpoint-every", type=int, default=200)
    args = parser.parse_args()

    os.environ["TMKI_OCR_MODE"] = "local"

    if not args.archive.is_dir():
        print(f"Архив не найден: {args.archive}", file=sys.stderr)
        return 1

    state_path = args.output / "reindex-state.json"
    if state_path.is_file() and not args.no_resume:
        import json

        prev = json.loads(state_path.read_text(encoding="utf-8"))
        n = len(prev.get("processed", []))
        print(f"Resume: {n} файлов уже обработано, stats={prev.get('stats')}", flush=True)

    print("Сканирование архива и re-index (TMKI_OCR_MODE=local)...", flush=True)

    from tmki_ingest import reindex_regulations_full
    from tmki_policy import build_policy_context, load_org_snapshot
    from tmki_rag import FolderAclContext, load_folder_catalog, load_folder_grants

    snapshot = load_org_snapshot(ROOT / "schemas/org/examples/satimol-snapshot.example.json")
    ctx = build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )
    acl = FolderAclContext.from_catalog(
        load_folder_catalog(ROOT / "schemas/document/examples/satimol-folders.example.json"),
        load_folder_grants(ROOT / "schemas/org/examples/satimol-folder-grants.example.json"),
        as_of=date(2025, 9, 10),
    )

    started = time.perf_counter()

    def progress(payload: dict) -> None:
        if payload.get("phase") == "scan_done":
            print(f"  Кандидатов: {payload['total_candidates']}", flush=True)
            return
        s = payload["stats"]
        print(
            f"  [{payload['file_index']}/{payload['total_candidates']}] "
            f"imported={s['imported']} skip_temp={s.get('skip_temp', 0)} "
            f"ocr_failed={s['ocr_failed']} err={s['errors']}",
            flush=True,
        )

    result = reindex_regulations_full(
        args.archive,
        policy_context=ctx,
        classification="restricted",
        folder_id="folder_ms_open",
        folder_acl=acl,
        output_dir=args.output,
        limit=args.limit,
        resume=not args.no_resume,
        checkpoint_every=args.checkpoint_every,
        on_progress=progress,
    )

    elapsed = time.perf_counter() - started
    print(
        f"\nRe-index за {elapsed:.1f}s\n"
        f"  imported: {result['imported_count']}\n"
        f"  ocr_failed: {result['ocr_failed_count']}\n"
        f"  chunks: {result['chunks_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
