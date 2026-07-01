#!/usr/bin/env python3
"""Запуск агента Legal Corpus Curator (еженедельный мониторинг нормативной базы)."""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Legal Corpus Curator — weekly RF law monitor")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from tmki_legal import run_legal_corpus_curator

    result = run_legal_corpus_curator(dry_run=args.dry_run)
    print(f"checked: {result['checked']}  changed: {result['changed']}  errors: {result['errors']}")
    for u in result["updates"]:
        print(f"  [{u['update_type']}] {u['doc_key']}: {u.get('title', '')[:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
