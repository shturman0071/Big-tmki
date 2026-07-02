#!/usr/bin/env python3
"""Однократное заполнение doc-catalog.json по reindex-state (doc_id → путь)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build doc-catalog cache from reindex processed list")
    parser.add_argument("--artifacts", type=Path, default=RUNTIME / "artifacts" / "regulations-import")
    parser.add_argument("--limit", type=int, default=0, help="Max new mappings (0 = all missing)")
    parser.add_argument("--batch", type=int, default=200, help="Save cache every N entries")
    args = parser.parse_args()

    from tmki_rag.doc_catalog import DocCatalog

    catalog = DocCatalog.load(artifacts_dir=args.artifacts)
    before = len(catalog.by_doc_id)
    print(f"doc-catalog before: {before} entries")
    added = catalog.warm_from_processed(limit=args.limit or 0, save_every=args.batch)
    after = len(catalog.by_doc_id)
    print(f"doc-catalog after: {after} entries (+{added})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
