#!/usr/bin/env python3
"""Панель всех операций TMKI: индексация, сервисы, фоновые задачи.

Примеры:
  python scripts/watch_tmki_ops.py
  python scripts/watch_tmki_ops.py --interval 3
  make watch-ops
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(RUNTIME))
sys.path.insert(0, str(SCRIPTS))

from ops_registry import OPS_PATH, load_jobs, upsert_job

STATE_PATH = RUNTIME / "artifacts" / "demo" / "load-skru2-state.json"
VKS_STATE_PATH = RUNTIME / "artifacts" / "demo" / "load-vks-state.json"
VKS_CHUNKS = RUNTIME / "artifacts" / "vks-import" / "chunks-v2.json"
QA_EVAL_STATE = RUNTIME / "artifacts" / "demo" / "qa-eval-state.json"
CHUNKS_V2 = RUNTIME / "artifacts" / "regulations-import" / "chunks-v2.json"
DEMO_PORT = int(os.environ.get("TMKI_DEMO_PORT", "8770"))
PAUSE_PATH = RUNTIME / "artifacts" / "demo" / "demo-paused.json"

PROCESS_WATCHLIST: list[tuple[str, str]] = [
    ("load_skru2_to_chunks.py", "Индексация chunks→PG"),
    ("reindex_regulations_local.py", "Re-index архива"),
    ("qa_eval_runner.py", "QA eval"),
    ("tmki_demo", "Demo UI"),
    ("eval_pdf_oxide_poc.py", "PoC pdf-oxide"),
    ("eval_hitk.py", "Eval Hit@K"),
    ("legal_corpus_curator.py", "Legal corpus"),
    ("ops_runner.py", "Ops runner"),
    ("pytest", "Pytest"),
    ("watch_tmki_ops.py", "Панель ops"),
    ("watch_load_skru2.py", "Монитор (legacy)"),
]


def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _bar(pct: float, width: int = 36) -> str:
    pct = max(0.0, min(100.0, pct))
    filled = int(width * pct / 100)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def _fmt_eta(seconds: float | None) -> str:
    if seconds is None or seconds < 0 or seconds > 86400 * 14:
        return "—"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}ч {m}м"
    if m:
        return f"{m}м {s}с"
    return f"{s}с"


def _python_processes() -> list[str]:
    if os.name != "nt":
        try:
            out = subprocess.check_output(["ps", "-ax", "-o", "command="], text=True, stderr=subprocess.DEVNULL)
            return [ln for ln in out.splitlines() if "python" in ln.lower()]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []
    try:
        out = subprocess.check_output(
            ["wmic", "process", "where", "name='python.exe'", "get", "CommandLine"],
            text=True,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return [ln.strip() for ln in out.splitlines() if ln.strip() and ln.strip() != "CommandLine"]
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return []


def _detect_running() -> dict[str, bool]:
    lines = _python_processes()
    blob = "\n".join(lines).lower()
    return {marker: marker.lower() in blob for marker, _ in PROCESS_WATCHLIST}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _load_state() -> dict[str, Any]:
    return _load_json(STATE_PATH)


def _load_vks_state() -> dict[str, Any]:
    return _load_json(VKS_STATE_PATH)


def _load_qa_eval() -> dict[str, Any]:
    return _load_json(QA_EVAL_STATE)


def _total_chunks(path: Path = CHUNKS_V2) -> int:
    if not path.is_file():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        chunks = data.get("chunks", data if isinstance(data, list) else [])
        return len(chunks) if isinstance(chunks, list) else 0
    except (OSError, json.JSONDecodeError):
        return 0


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


def _http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _demo_paused() -> str | None:
    if not PAUSE_PATH.is_file():
        return None
    try:
        data = json.loads(PAUSE_PATH.read_text(encoding="utf-8"))
        if data.get("paused"):
            return str(data.get("reason") or "пауза")
    except (OSError, json.JSONDecodeError):
        pass
    return None


def _status_icon(ok: bool | None) -> str:
    if ok is True:
        return "OK"
    if ok is False:
        return "DOWN"
    return "?"


def _job_status_icon(status: str) -> str:
    return {
        "running": ">>",
        "done": "OK",
        "failed": "!!",
        "queued": "..",
        "skipped": "--",
    }.get(status, "  ")


def _render(
    *,
    total: int,
    state: dict[str, Any],
    vks_state: dict[str, Any],
    vks_total: int,
    qa_eval: dict[str, Any],
    pg: dict[str, int],
    proc: dict[str, bool],
    jobs_data: dict[str, Any],
    rate_per_min: float | None,
    ollama_ok: bool,
    demo_ok: bool,
    demo_pause: str | None,
) -> str:
    offset = int(state.get("offset") or 0)
    skru2 = pg.get("skru-2", 0)
    vks_pg = pg.get("vks", 0)
    pct = 100.0 * offset / total if total else 0.0
    remaining = max(0, total - offset)
    eta = (remaining / rate_per_min * 60) if rate_per_min and rate_per_min > 0 else None
    loader_on = proc.get("load_skru2_to_chunks.py", False)
    vks_offset = int(vks_state.get("offset") or 0)
    vks_pct = 100.0 * vks_offset / vks_total if vks_total else 0.0

    lines = [
        "=" * 64,
        "  TMKI OPS — панель операций",
        "=" * 64,
        f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "  СЕРВИСЫ",
        f"    PostgreSQL   {_status_icon(bool(pg))}   skru-2={skru2:,}  vks={vks_pg:,}  test_docs={pg.get('test_docs', 0)}",
        f"    Ollama       {_status_icon(ollama_ok)}",
    ]
    if demo_pause and not demo_ok:
        lines.append(f"    Demo :{DEMO_PORT}    PAUSE  ({demo_pause})")
    else:
        lines.append(f"    Demo :{DEMO_PORT}    {_status_icon(demo_ok)}   http://127.0.0.1:{DEMO_PORT}/")
    lines += [
        "  ИНДЕКСАЦИЯ СКРУ-2",
        f"    Процесс: {'РАБОТАЕТ' if loader_on else 'НЕ ЗАПУЩЕН'}   embed-batch={state.get('embed_batch', '?')}",
        f"    {offset:,} / {total:,}  ({pct:.1f}%)  {_bar(pct)}",
    ]
    if rate_per_min and rate_per_min > 0:
        lines.append(f"    ~{rate_per_min:.0f} ч/мин  ETA {_fmt_eta(eta)}")
    else:
        lines.append("    скорость: оценка после 2 опросов...")
    if vks_total:
        lines += [
            "  ИНДЕКСАЦИЯ ВКС",
            f"    {vks_offset:,} / {vks_total:,}  ({vks_pct:.1f}%)  {_bar(vks_pct)}",
        ]
    qa_cursor = int(qa_eval.get("cursor") or 0)
    qa_total = int(qa_eval.get("total") or 0)
    if qa_total:
        lines += [
            "  QA EVAL (СКРУ-2)",
            f"    {qa_eval.get('passed', 0)}✓ {qa_eval.get('failed', 0)}✗  ({qa_cursor}/{qa_total})"
            + ("  RUN" if qa_eval.get("running") else ""),
        ]
    lines += ["", "  ПРОЦЕССЫ PYTHON"]

    for marker, label in PROCESS_WATCHLIST:
        if marker in ("watch_tmki_ops.py", "watch_load_skru2.py"):
            continue
        on = proc.get(marker, False)
        mark = "RUN" if on else "   "
        lines.append(f"    [{mark}] {label}")

    lines += ["", "  ФОНОВЫЕ ЗАДАЧИ (ops-jobs.json)"]
    jobs = jobs_data.get("jobs") or []
    if not jobs:
        lines.append("    (нет записей — запустите: python scripts/ops_runner.py)")
    else:
        for job in jobs[-8:]:
            prog = job.get("progress")
            bar = _bar(prog * 100, width=20) if isinstance(prog, (int, float)) else ""
            detail = job.get("detail") or ""
            icon = _job_status_icon(str(job.get("status") or ""))
            line = f"    [{icon}] {job.get('label', job.get('id', '?'))}"
            if bar:
                line += f"  {bar} {prog * 100:.0f}%"
            elif detail:
                line += f"  {detail}"
            lines.append(line)

    lines += [
        "",
        f"  Реестр: {OPS_PATH.name}  |  Ctrl+C — выход",
        "=" * 64,
    ]
    return "\n".join(lines)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Панель операций TMKI")
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    total = _total_chunks()
    vks_total = _total_chunks(VKS_CHUNKS)
    if total == 0 and vks_total == 0:
        print(f"Нет chunks-v2: {CHUNKS_V2} / {VKS_CHUNKS}", file=sys.stderr)
        return 1

    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    prev_offset: int | None = None
    prev_ts: float | None = None
    rate_per_min: float | None = None

    try:
        while True:
            state = _load_state()
            vks_state = _load_vks_state()
            qa_eval = _load_qa_eval()
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
                pg = {}
                print(f"PG: {exc}", file=sys.stderr)

            proc = _detect_running()
            loader_on = proc.get("load_skru2_to_chunks.py", False)
            if loader_on:
                upsert_job(
                    "load-skru2",
                    label="Индексация СКРУ-2",
                    status="running",
                    progress=offset / total if total else 0,
                    detail=f"{offset:,}/{total:,}",
                )
            jobs_data = load_jobs()
            ollama_ok = _http_ok(f"{ollama_url.rstrip('/')}/api/tags")
            demo_ok = _http_ok(f"http://127.0.0.1:{DEMO_PORT}/")
            demo_pause = _demo_paused()

            _clear()
            print(
                _render(
                    total=total,
                    state=state,
                    vks_state=vks_state,
                    vks_total=vks_total,
                    qa_eval=qa_eval,
                    pg=pg,
                    proc=proc,
                    jobs_data=jobs_data,
                    rate_per_min=rate_per_min,
                    ollama_ok=ollama_ok,
                    demo_ok=demo_ok,
                    demo_pause=demo_pause,
                )
            )
            if args.once:
                break
            time.sleep(max(1.0, args.interval))
    except KeyboardInterrupt:
        print("\nСтоп.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
