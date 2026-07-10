#!/usr/bin/env python3
"""Сверка архива СКРУ-2 с reindex-state и pgvector."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME))

from tmki_ingest.regulations import CATALOG_ONLY_EXTENSIONS, INGEST_EXTENSIONS
from tmki_ingest.reindex_progress import build_reindex_report


def main() -> int:
    archive = Path(r"D:\Курсор\СКРУ-2")
    state_path = RUNTIME / "artifacts" / "regulations-import" / "reindex-state.json"
    hb = state_path.parent / "reindex-heartbeat.json"
    lock = state_path.parent / "reindex.lock"

    if not archive.is_dir():
        print(f"Архив не найден: {archive}")
        return 1
    if not state_path.is_file():
        print(f"reindex-state не найден: {state_path}")
        return 1

    state = json.loads(state_path.read_text(encoding="utf-8"))
    report = build_reindex_report(state_path=state_path, heartbeat_path=hb, lock_path=lock)
    processed = {str(p).replace("\\", "/") for p in (state.get("processed") or [])}
    stats = state.get("stats") or {}

    allowed = {e.lower() for e in INGEST_EXTENSIONS}
    catalog = {e.lower() for e in CATALOG_ONLY_EXTENSIONS}

    on_disk_ingest: list[str] = []
    on_disk_catalog = 0
    on_disk_other = 0
    for p in archive.rglob("*"):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        rel = str(p.relative_to(archive)).replace("\\", "/")
        if ext in allowed:
            on_disk_ingest.append(rel)
        elif ext in catalog:
            on_disk_catalog += 1
        else:
            on_disk_other += 1

    disk_ingest = set(on_disk_ingest)
    missing = sorted(disk_ingest - processed)
    extra = sorted(processed - disk_ingest)

    print("=== ARCHIVE D:\\Курсор\\СКРУ-2 ===")
    print(f"ingest-файлов на диске:     {len(disk_ingest)}")
    print(f"catalog-only на диске:      {on_disk_catalog}")
    print(f"прочие расширения:          {on_disk_other}")
    print()
    print("=== REINDEX STATE ===")
    print(f"archive_root:               {state.get('archive_root')}")
    print(f"total_candidates:           {state.get('total_candidates')}")
    print(f"processed (список):         {len(processed)}")
    print(f"imported / chunks_v2:       {stats.get('imported')} / {stats.get('chunks_v2')}")
    print(
        f"skip_temp / ocr_failed:     {stats.get('skip_temp')} / {stats.get('ocr_failed')}"
    )
    print(f"errors:                     {stats.get('errors')}")
    print(f"live_progress / pct:        {report.get('live_progress')} / {round(float(report.get('percent') or 0), 1)}%")
    print(f"complete:                   {report.get('complete')}")
    lock_pid = report.get("lock_pid")
    print(f"lock active:                {bool(lock_pid)} (pid={lock_pid})")
    print(f"current_file:               {report.get('current_file')}")
    print()
    print("=== РАЗРЫВ ===")
    print(f"на диске, но НЕ в processed: {len(missing)}")
    print(f"в processed, но НЕ на диске: {len(extra)}")
    if missing[:10]:
        print("примеры не проиндексированных:")
        for rel in missing[:10]:
            print(f"  - {rel}")

    try:
        from tmki_runtime.rag_env import load_rag_config

        load_rag_config(override=False)
        url = os.environ.get("DATABASE_URL")
        if url:
            import psycopg2

            conn = psycopg2.connect(url, connect_timeout=5)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(DISTINCT COALESCE(
                    NULLIF(metadata->>'source_relative_path', ''),
                    NULLIF(doc_path, ''),
                    doc_id
                ))
                FROM chunks
                WHERE corpus_id=%s
                """,
                ("skru-2",),
            )
            pg_files = int(cur.fetchone()[0])
            cur.execute("SELECT COUNT(*) FROM chunks WHERE corpus_id=%s", ("skru-2",))
            pg_chunks = int(cur.fetchone()[0])
            cur.close()
            conn.close()
            print()
            print("=== PGVECTOR (corpus skru-2) ===")
            print(f"уникальных файлов:          {pg_files}")
            print(f"чанков:                     {pg_chunks}")
    except Exception as exc:
        print(f"\npgvector: недоступен ({exc})")

    if report.get("complete") and not missing:
        print("\nИТОГ: индексация полная.")
        return 0
    print("\nИТОГ: индексация НЕ полная.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
