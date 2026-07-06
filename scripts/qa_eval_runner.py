#!/usr/bin/env python3
"""CLI: последовательный прогон Q→A eval (СКРУ-2 ground-truth).

Примеры:
  python scripts/qa_eval_runner.py --one
  python scripts/qa_eval_runner.py --all
  python scripts/qa_eval_runner.py --reset
  python scripts/qa_eval_runner.py --watch --interval 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(RUNTIME))

from tmki_demo.qa_eval import get_eval_snapshot, reset_eval, run_all, run_one  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="QA eval runner (ground-truth)")
    parser.add_argument("--corpus", default="skru-2")
    parser.add_argument("--llm", default="stub", choices=("stub", "ollama"))
    parser.add_argument("--one", action="store_true", help="Один вопрос")
    parser.add_argument("--all", action="store_true", help="Все вопросы подряд")
    parser.add_argument("--reset", action="store_true", help="Сбросить state")
    parser.add_argument("--watch", action="store_true", help="Периодически печатать snapshot")
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()

    if args.reset:
        snap = reset_eval(corpus_id=args.corpus)
        print(json.dumps(snap, ensure_ascii=False, indent=2))
        return 0

    if args.all:
        snap = run_all(corpus_id=args.corpus, llm=args.llm)
        print(
            f"Готово: {snap['passed']} pass {snap['failed']} fail / {snap['total']} "
            f"(failures: {len(snap.get('failures') or [])})"
        )
        return 0 if snap.get("failed", 0) == 0 else 1

    if args.one:
        snap = run_one(corpus_id=args.corpus, llm=args.llm)
        last = snap.get("last") or {}
        mark = "OK" if last.get("passed") else "FAIL"
        print(f"{mark} [{snap['cursor']}/{snap['total']}] {last.get('reason', '')}")
        return 0

    if args.watch:
        try:
            while True:
                snap = get_eval_snapshot()
                print(
                    f"{snap.get('updated_at', '')} "
                    f"{snap['cursor']}/{snap['total']} "
                    f"pass={snap['passed']} fail={snap['failed']} "
                    f"running={snap.get('running')}"
                )
                time.sleep(max(1.0, args.interval))
        except KeyboardInterrupt:
            print("\nСтоп.")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
