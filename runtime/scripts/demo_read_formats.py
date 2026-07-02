#!/usr/bin/env python3
"""Демо: чтение файлов разных форматов."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_SAMPLES = Path(__file__).resolve().parents[1] / "artifacts" / "demo-samples"


def main() -> int:
    parser = argparse.ArgumentParser(description="Demo: read multiple file formats")
    parser.add_argument("paths", nargs="*", type=Path, help="Файлы для чтения")
    parser.add_argument("--samples", action="store_true", help="Встроенные demo-samples")
    parser.add_argument("--matrix", action="store_true", help="Таблица поддерживаемых форматов")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from tmki_document.reader import format_support_matrix, read_file

    if args.matrix:
        rows = format_support_matrix()
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            print("Формат     Статус              Примечание")
            print("-" * 55)
            for row in rows:
                print(f"{row['extension']:<10} {row['status']:<19} {row['note']}")
        return 0

    paths = list(args.paths)
    if args.samples or not paths:
        if DEFAULT_SAMPLES.is_dir():
            paths.extend(sorted(DEFAULT_SAMPLES.iterdir()))
        else:
            print(f"demo-samples не найден: {DEFAULT_SAMPLES}", file=sys.stderr)
            return 1

    results = [read_file(p) for p in paths if p.is_file()]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    print("TMKI — чтение файлов (demo)\n")
    for row in results:
        status = "ok" if row.get("readable") else row.get("category", "skip")
        print(f"  [{status}] {Path(row['path']).name}")
        print(f"         method={row.get('method')} chars={row.get('chars', 0)}")
        if row.get("detail"):
            print(f"         {row['detail']}")
        elif row.get("preview"):
            line = row["preview"].replace("\n", " ")[:120]
            print(f"         «{line}»")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
