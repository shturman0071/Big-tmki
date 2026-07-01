#!/usr/bin/env python3
"""Desktop sync: папка на рабочем столе → локальный сервер (каждые 5 с)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description="Desktop folder sync agent")
    parser.add_argument("--employee-id", default="emp_litovsky_d")
    parser.add_argument("--display-name", default="Литовский Д.")
    parser.add_argument("--once", action="store_true", help="Один проход без цикла")
    parser.add_argument("--interval", type=int, default=None)
    parser.add_argument("--ingest", action="store_true", help="Ingest новых файлов в RAG после sync")
    args = parser.parse_args()

    from tmki_desktop_sync import DesktopSyncWatcher, default_server_path, desktop_folder_for_employee

    desk = desktop_folder_for_employee(args.display_name)
    server = default_server_path(args.employee_id)
    print(f"desktop: {desk}")
    print(f"server:  {server}")

    on_synced = None
    if args.ingest:
        from tmki_desktop_sync.ingest_hook import ingest_synced_file

        def on_synced(_src: Path, dest: Path) -> None:
            result = ingest_synced_file(dest)
            print(f"  ingest {dest.name}: {result['ingest_status']} chunks={result['chunks']}", flush=True)

    watcher = DesktopSyncWatcher(
        desktop_path=desk,
        server_path=server,
        employee_id=args.employee_id,
        interval_sec=args.interval,
        on_file_synced=on_synced,
    )

    if args.once:
        records = watcher.sync_once()
        copied = sum(1 for r in records if r.action == "copied")
        print(f"synced: {copied}/{len(records)} files")
        return 0

    print(f"loop every {watcher.interval_sec}s (Ctrl+C to stop)")
    try:
        watcher.run_loop()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
