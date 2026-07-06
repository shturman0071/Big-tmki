#!/usr/bin/env python3
"""Мониторинг загрузки СКРУ-2 в PostgreSQL (load_skru2_to_chunks) в реальном времени.

Устарело: для полной панели используйте `python scripts/watch_tmki_ops.py`.

Примеры:
  python scripts/watch_tmki_ops.py      # рекомендуется
  python scripts/watch_load_skru2.py    # только индекс
  python scripts/watch_load_skru2.py --interval 10
  python scripts/watch_load_skru2.py --once
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(RUNTIME))

STATE_PATH = RUNTIME / "artifacts" / "demo" / "load-skru2-state.json"
CHUNKS_V2 = RUNTIME / "artifacts" / "regulations-import" / "chunks-v2.json"
LOADER_MARKER = "load_skru2_to_chunks.py"


def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.is_file():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _total_chunks() -> int:
    if not CHUNKS_V2.is_file():
        return 0
    try:
        data = json.loads(CHUNKS_V2.read_text(encoding="utf-8"))
        chunks = data.get("chunks", data if isinstance(data, list) else [])
        return len(chunks) if isinstance(chunks, list) else 0
    except (OSError, json.JSONDecodeError):
        return 0


def _loader_running() -> bool:
    if os.name != "nt":
        try:
            out = subprocess.check_output(["pgrep", "-f", LOADER_MARKER], text=True, stderr=subprocess.DEVNULL)
            return bool(out.strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    try:
        out = subprocess.check_output(
            ["wmic", "process", "where", "name='python.exe'", "get", "CommandLine"],
            text=True,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return LOADER_MARKER.replace(".py", "") in out or LOADER_MARKER in out
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False


def _pg_counts() -> dict[str, int]:
    from tmki_runtime.rag_env import load_rag_config

    load_rag_config(override=False)
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        return {}
    import psycopg2

    conn = psycopg2.connect(db_url, connect_timeout=5)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT corpus_id, COUNT(*) FROM chunks GROUP BY corpus_id ORDER BY COUNT(*) DESC")
    rows = {str(r[0] or "(null)"): int(r[1]) for r in cur.fetchall()}
    cur.close()
    conn.close()
    return rows


def _bar(pct: float, width: int = 40) -> str:
    pct = max(0.0, min(100.0, pct))
    filled = int(width * pct / 100)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def _fmt_eta(seconds: float | None) -> str:
    if seconds is None or seconds < 0 or seconds > 86400 * 14:
        return "-"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}ч {m}м"
    if m:
        return f"{m}м {s}с"
    return f"{s}с"


def _render(
    *,
    total: int,
    state: dict[str, Any],
    pg: dict[str, int],
    running: bool,
    rate_per_min: float | None,
) -> str:
    offset = int(state.get("offset") or 0)
    updated = state.get("updated_at") or "—"
    skru2 = pg.get("skru-2", 0)
    test_docs = pg.get("test_docs", 0)
    pct = 100.0 * offset / total if total else 0.0
    pg_pct = 100.0 * skru2 / total if total else 0.0
    remaining = max(0, total - offset)
    eta = (remaining / rate_per_min * 60) if rate_per_min and rate_per_min > 0 else None

    lines = [
        "=" * 60,
        "  СКРУ-2 -> PostgreSQL (load_skru2_to_chunks)",
        "=" * 60,
        f"  Время:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"  Процесс:   {'РАБОТАЕТ' if running else 'НЕ ЗАПУЩЕН'}",
        f"  Embed batch: {state.get('embed_batch', state.get('workers', '?'))}",
        "",
        f"  Checkpoint offset:  {offset:,} / {total:,}  ({pct:.1f}%)",
        f"  {_bar(pct)}",
        f"  state updated:      {updated}",
        "",
        f"  В базе PG skru-2:   {skru2:,}  ({pg_pct:.1f}%)",
        f"  В базе PG test_docs:{test_docs:,}",
        "",
    ]
    if rate_per_min is not None and rate_per_min > 0:
        lines.append(f"  Скорость:           ~{rate_per_min:.0f} чанков/мин")
        lines.append(f"  Осталось (оценка):  {_fmt_eta(eta)}")
    else:
        lines.append("  Скорость:           жду данные (2+ опроса)...")
    lines += [
        "",
        "  Ctrl+C — выход",
        "=" * 60,
    ]
    return "\n".join(lines)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Мониторинг загрузки СКРУ-2 в PG")
    parser.add_argument("--interval", type=float, default=5.0, help="Интервал опроса, сек (default: 5)")
    parser.add_argument("--once", action="store_true", help="Один снимок и выход")
    args = parser.parse_args()

    total = _total_chunks()
    if total == 0:
        print(f"Нет chunks-v2: {CHUNKS_V2}", file=sys.stderr)
        return 1

    prev_offset: int | None = None
    prev_ts: float | None = None
    rate_per_min: float | None = None

    try:
        while True:
            state = _load_state()
            offset = int(state.get("offset") or 0)
            now = time.time()

            if prev_offset is not None and prev_ts is not None:
                dt = now - prev_ts
                if dt > 0 and offset >= prev_offset:
                    rate_per_min = (offset - prev_offset) / dt * 60.0

            prev_offset = offset
            prev_ts = now

            try:
                pg = _pg_counts()
            except Exception as exc:
                pg = {"(ошибка PG)": 0}
                print(f"PostgreSQL: {exc}", file=sys.stderr)

            running = _loader_running()
            _clear()
            print(_render(total=total, state=state, pg=pg, running=running, rate_per_min=rate_per_min))

            if args.once:
                break
            time.sleep(max(1.0, args.interval))
    except KeyboardInterrupt:
        print("\nСтоп.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
