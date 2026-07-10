# -*- coding: utf-8 -*-
"""CLI: индексация to-do-list.xlsx + sync задач Аксенова в Kanboard."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME))
sys.path.insert(0, str(RUNTIME.parent))

from tmki_runtime.rag_env import load_rag_config

load_rag_config(override=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reindex", action="store_true", help="Также переиндексировать xlsx в skru-2")
    args = parser.parse_args()
    from tmki_demo.todo_kanboard_sync import sync_from_xlsx

    result = sync_from_xlsx(reindex=args.reindex)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
