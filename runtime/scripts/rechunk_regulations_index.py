#!/usr/bin/env python3
"""Пересобрать chunks-v2.json: полный текст документов, мульти-чанки (без повторного OCR API)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

DEFAULT_ARTIFACTS = RUNTIME / "artifacts" / "regulations-import"


def _list_archive_files(archive_root: Path) -> list[str]:
    from tmki_ingest.regulations import INGEST_EXTENSIONS

    allowed = {ext.lower() for ext in INGEST_EXTENSIONS}
    return [
        str(p.relative_to(archive_root)).replace("\\", "/")
        for p in sorted(archive_root.rglob("*"))
        if p.is_file() and p.suffix.lower() in allowed
    ]


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, list[str]]:
    from tmki_rag.corpus_policy import get_corpus, resolve_corpus_archive, resolve_corpus_artifacts_dir
    from tmki_rag.doc_catalog import resolve_archive_root

    if args.corpus:
        profile = get_corpus(args.corpus)
        artifacts = resolve_corpus_artifacts_dir(profile.corpus_id)
        archive_root = resolve_corpus_archive(profile.corpus_id)
    else:
        artifacts = args.artifacts
        archive_root = resolve_archive_root(artifacts)

    if not archive_root or not archive_root.is_dir():
        raise SystemExit(f"archive not found: {archive_root}")

    state_path = artifacts / "reindex-state.json"
    processed: list[str] = []
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        processed = [str(p) for p in (state.get("processed") or [])]
    elif args.scan_archive:
        processed = _list_archive_files(archive_root)
        artifacts.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "schema_version": "0.1",
                    "archive_root": str(archive_root),
                    "processed": processed,
                    "total_candidates": len(processed),
                    "stats": {"indexed": 0, "errors": 0},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Created reindex-state: {len(processed)} files in {archive_root}", flush=True)
    else:
        raise SystemExit(f"reindex-state not found: {state_path} (use --scan-archive)")

    out_path = args.output or (artifacts / "chunks-v2.json")
    if args.limit:
        processed = processed[: args.limit]
    return artifacts, archive_root, out_path, processed


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-chunk regulations archive with full text windows")
    parser.add_argument("--corpus", choices=["skru-2", "arm-ks"], default=None, help="корпус (skru-2 / arm-ks)")
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--output", type=Path, default=None, help="default: artifacts/chunks-v2.json")
    parser.add_argument("--limit", type=int, default=0, help="max files (0 = all)")
    parser.add_argument("--resume", action="store_true", help="skip paths already in existing chunks")
    parser.add_argument(
        "--scan-archive",
        action="store_true",
        help="если нет reindex-state — просканировать архив и создать state",
    )
    parser.add_argument("--save-every", type=int, default=200, help="промежуточное сохранение chunks")
    args = parser.parse_args()

    from tmki_ingest.chunking import build_chunks_from_ocr
    from tmki_ingest.dedup import compute_content_hash
    from tmki_ocr.extractors import extract_local_text, guess_suffix
    from tmki_policy import build_policy_context, load_org_snapshot

    artifacts, archive_root, out_path, processed = _resolve_paths(args)
    existing_doc_paths: set[str] = set()
    if args.resume and out_path.is_file():
        try:
            data = json.loads(out_path.read_text(encoding="utf-8"))
            old = data if isinstance(data, list) else data.get("chunks", [])
            for ch in old:
                rel = ch.get("source_relative_path")
                if rel:
                    existing_doc_paths.add(str(rel))
        except (OSError, json.JSONDecodeError):
            pass

    root = RUNTIME.parent
    snapshot = load_org_snapshot(root / "schemas/org/examples/satimol-snapshot.example.json")
    policy = build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )

    all_chunks: list[dict] = []
    errors = 0
    for i, rel in enumerate(processed, start=1):
        if args.resume and rel in existing_doc_paths:
            continue
        full = archive_root / rel
        if not full.is_file():
            errors += 1
            continue
        try:
            raw = full.read_bytes()
            suffix = guess_suffix(raw, full.name)
            extracted = extract_local_text(raw, suffix=suffix)
            text = (extracted.get("text") or "").strip()
            if not text:
                errors += 1
                continue
            content_hash = compute_content_hash(raw)
            doc_id = f"doc_{content_hash[7:19]}"
            ocr_result = {"doc_id": doc_id, "ocr_status": "completed"}
            chunks = build_chunks_from_ocr(
                ocr_result,
                company_id=policy["company_id"],
                project_id=policy["project_id"],
                department_id=policy.get("department_id"),
                folder_id=None,
                classification="internal",
                markdown=text,
            )
            for chunk in chunks:
                chunk["source_relative_path"] = rel.replace("\\", "/")
                chunk["source_file_name"] = full.name
            all_chunks.extend(chunks)
        except OSError:
            errors += 1
            continue
        if i % 200 == 0:
            print(f"  {i}/{len(processed)} files → {len(all_chunks)} chunks", flush=True)
        if args.save_every and i % args.save_every == 0:
            _flush_chunks(out_path, all_chunks)

    if args.resume and out_path.is_file():
        try:
            data = json.loads(out_path.read_text(encoding="utf-8"))
            prev = data if isinstance(data, list) else data.get("chunks", [])
            all_chunks = prev + all_chunks
        except (OSError, json.JSONDecodeError):
            pass

    payload = {"schema_version": "0.1", "chunks": all_chunks}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(all_chunks)} chunks to {out_path} (errors/skips: {errors})")
    return 0


def _flush_chunks(out_path: Path, chunks: list[dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"schema_version": "0.1", "chunks": chunks}, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
