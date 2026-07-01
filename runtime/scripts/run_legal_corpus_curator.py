#!/usr/bin/env python3
"""Запуск агента Legal Corpus Curator (еженедельный мониторинг нормативной базы)."""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Legal Corpus Curator — weekly RF law monitor")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--apply-ingest",
        action="store_true",
        help="После curator — ingest pending regulatory-updates в RAG",
    )
    args = parser.parse_args()

    from tmki_legal import apply_pending_legal_updates, run_legal_corpus_curator

    result = run_legal_corpus_curator(dry_run=args.dry_run)
    print(f"checked: {result['checked']}  changed: {result['changed']}  errors: {result['errors']}")
    for u in result["updates"]:
        print(f"  [{u['update_type']}] {u['doc_key']}: {u.get('title', '')[:60]}")

    if args.apply_ingest and not args.dry_run:
        ingest = apply_pending_legal_updates()
        print(
            f"ingest: pending={ingest['pending']} applied={ingest['applied']} failed={ingest['failed']}"
        )
        for row in ingest["results"]:
            print(f"  {row['doc_key']}: {row.get('ingest_status')} chunks={row.get('chunks', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
