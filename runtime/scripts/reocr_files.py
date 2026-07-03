#!/usr/bin/env python3
"""Пере-OCR и доиндексация выбранных файлов (сканы без текстового слоя)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-OCR selected files into corpus index")
    parser.add_argument("--corpus", choices=["skru-2", "arm-ks"], default="arm-ks")
    parser.add_argument("--match", action="append", default=[], help="подстрока в пути файла (можно несколько)")
    parser.add_argument("--reocr-failed", action="store_true", help="все файлы без чанков из reindex-state")
    parser.add_argument("--reocr-pdfs", action="store_true", help="все PDF из processed (повторный OCR, напр. с rus)")
    parser.add_argument("--ocr-mode", choices=["local", "http"], default="local")
    args = parser.parse_args()

    if str(RUNTIME) not in sys.path:
        sys.path.insert(0, str(RUNTIME))
    os.environ["TMKI_OCR_MODE"] = args.ocr_mode
    tessdata = RUNTIME / "tessdata"
    if (tessdata / "rus.traineddata").is_file():
        os.environ["TESSDATA_PREFIX"] = str(tessdata)
        os.environ.setdefault("TESSERACT_LANG", "rus+eng")
        print(f"TESSDATA_PREFIX={tessdata}", flush=True)

    from tmki_ingest import DedupStore, ingest_and_index
    from tmki_ingest.regulations import build_ingest_request
    from tmki_policy import build_policy_context, load_org_snapshot
    from tmki_rag import ChunkIndex, FolderAclContext, load_folder_catalog, load_folder_grants
    from tmki_rag.corpus_policy import get_corpus, resolve_corpus_archive, resolve_corpus_artifacts_dir

    corpus = get_corpus(args.corpus)
    archive = resolve_corpus_archive(args.corpus)
    artifacts = resolve_corpus_artifacts_dir(args.corpus)
    chunks_path = artifacts / "chunks-v2.json"
    state_path = artifacts / "reindex-state.json"

    if not archive.is_dir():
        print(f"Архив не найден: {archive}", file=sys.stderr)
        return 1

    indexed_paths: set[str] = set()
    chunks: list[dict] = []
    if chunks_path.is_file():
        data = json.loads(chunks_path.read_text(encoding="utf-8"))
        chunks = list(data.get("chunks") or [])
        indexed_paths = {c.get("source_relative_path", "") for c in chunks if c.get("source_relative_path")}

    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {"processed": [], "stats": {}}
    processed = list(state.get("processed") or [])

    targets: list[str] = []
    if args.reocr_failed:
        targets = [p for p in processed if p not in indexed_paths]
    if args.reocr_pdfs:
        targets.extend(p for p in processed if p.lower().endswith(".pdf"))
    for needle in args.match:
        targets.extend(p for p in processed if needle.lower() in p.lower())
    targets = sorted(set(targets))
    if not targets:
        print("Нет файлов для пере-OCR (укажите --match, --reocr-failed или --reocr-pdfs)", file=sys.stderr)
        return 2

    print(f"Re-OCR {len(targets)} file(s), mode={args.ocr_mode}", flush=True)

    index = ChunkIndex(chunks)
    dedup = DedupStore()
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

    stats = state.setdefault("stats", {})
    imported = 0
    failed = 0
    for rel in targets:
        full = archive / rel
        if not full.is_file():
            print(f"  skip missing: {rel}", flush=True)
            continue
        print(f"  OCR: {rel}", flush=True)
        try:
            raw = full.read_bytes()
            request = build_ingest_request(
                full,
                policy_context=ctx,
                classification="restricted",
                folder_id="folder_ms_open",
            )
            request["force_reprocess"] = True
            result = ingest_and_index(
                request,
                index,
                folder_acl=acl,
                dedup_store=dedup,
                raw_bytes=raw,
            )
            if result.chunks:
                imported += 1
                for chunk in result.chunks:
                    chunk["source_relative_path"] = rel.replace("\\", "/")
                    chunk["source_file_name"] = full.name
                chunks = [c for c in chunks if c.get("source_relative_path") != rel.replace("\\", "/")]
                chunks.extend(result.chunks)
                print(f"    +{len(result.chunks)} chunks", flush=True)
            else:
                failed += 1
                print("    no text extracted", flush=True)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"    error: {exc}", flush=True)

    chunks_path.parent.mkdir(parents=True, exist_ok=True)
    chunks_path.write_text(
        json.dumps({"schema_version": "0.1", "chunks": chunks}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    stats["imported"] = int(stats.get("imported", 0)) + imported
    stats["ocr_failed"] = max(0, int(stats.get("ocr_failed", 0)) - imported)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Done: +{imported} files, failed={failed}, total chunks={len(chunks)}")
    return 0 if imported else 1


if __name__ == "__main__":
    raise SystemExit(main())
