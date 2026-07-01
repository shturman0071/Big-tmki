#!/usr/bin/env python3
"""Полный импорт архива регламентов (stub OCR)."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARCHIVE = Path(r"D:\Курсор\ТМКИ оригнал")
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import"


def main() -> int:
    parser = argparse.ArgumentParser(description="TMKI full regulations import (stub OCR)")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=None, help="Max new imports (default: all)")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--checkpoint-every", type=int, default=100)
    parser.add_argument("--folder-id", default="folder_ms_open")
    parser.add_argument("--classification", default="restricted")
    args = parser.parse_args()

    if not args.archive.is_dir():
        print(f"Архив не найден: {args.archive}", file=sys.stderr)
        return 1

    args.output.mkdir(parents=True, exist_ok=True)
    state_path = args.output / "state.json"
    chunks_path = args.output / "chunks.json"

    from tmki_ingest import DedupStore, import_regulations_full, scan_regulations_archive
    from tmki_policy import build_policy_context, load_org_snapshot
    from tmki_rag import ChunkIndex, FolderAclContext, load_folder_catalog, load_folder_grants

    manifest = scan_regulations_archive(args.archive)
    print(
        f"Архив: {args.archive}\n"
        f"Всего файлов: {manifest['total_files']}, ingest_candidate: {manifest['stats']['ingest_candidate']}"
    )

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

    index = ChunkIndex()
    dedup = DedupStore()
    started = time.perf_counter()

    def progress(payload: dict) -> None:
        s = payload["stats"]
        print(
            f"  [{payload['file_index']}/{payload['total_candidates']}] "
            f"imported={s['imported']} dup={s['duplicate']} err={s['errors']}",
            flush=True,
        )

    result = import_regulations_full(
        args.archive,
        policy_context=ctx,
        classification=args.classification,
        folder_id=args.folder_id,
        folder_acl=acl,
        dedup_store=dedup,
        index=index,
        limit=args.limit,
        state_path=state_path,
        chunks_path=chunks_path,
        checkpoint_every=args.checkpoint_every,
        on_progress=progress,
        resume=not args.no_resume,
    )

    elapsed = time.perf_counter() - started
    print(
        f"\nГотово за {elapsed:.1f}s\n"
        f"  imported: {result['imported_count']}\n"
        f"  duplicate: {result['duplicate_count']}\n"
        f"  rejected: {result['rejected_count']}\n"
        f"  ocr_failed: {result['ocr_failed_count']}\n"
        f"  too_large: {result['too_large_count']}\n"
        f"  errors: {result['error_count']}\n"
        f"  chunks in index: {result['chunks_in_index']}\n"
        f"  state: {result['state_path']}\n"
        f"  chunks: {result['chunks_path']}"
    )
    return 0 if result["error_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
