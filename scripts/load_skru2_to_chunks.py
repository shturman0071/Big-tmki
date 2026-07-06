#!/usr/bin/env python3
"""Загрузка chunks-v2 (СКРУ-2) в PostgreSQL chunks + Ollama 768-dim.

Использует уже собранный runtime/artifacts/regulations-import/chunks-v2.json
(текст из OCR), без повторного чтения архива.

Примеры:
  python scripts/load_skru2_to_chunks.py --limit 3000          # пробный индекс
  python scripts/load_skru2_to_chunks.py --resume              # продолжить
  python scripts/load_skru2_to_chunks.py --resume --embed-batch 48  # быстрее (batch /api/embed)
  python scripts/load_skru2_to_chunks.py --replace-corpus    # перезаписать skru-2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(RUNTIME))

from tmki_runtime.rag_env import load_rag_config

load_rag_config(override=False)

DEFAULT_STATE_PATH = RUNTIME / "artifacts" / "demo" / "load-skru2-state.json"
_active_state_path: Path = DEFAULT_STATE_PATH
DEFAULT_CHUNKS_V2 = RUNTIME / "artifacts" / "regulations-import" / "chunks-v2.json"


def state_path_for(corpus: str) -> Path:
    if corpus == "skru-2":
        return DEFAULT_STATE_PATH
    safe = corpus.replace("/", "-")
    return RUNTIME / "artifacts" / "demo" / f"load-{safe}-state.json"


def set_state_path(path: Path) -> None:
    global _active_state_path
    _active_state_path = path

_thread_local = threading.local()
INSERT_SQL = """
    INSERT INTO chunks (
        chunk_id, corpus_id, doc_id, doc_path, content, embedding,
        embedding_dim, page, section, has_table, metadata, indexed_at, updated_at
    ) VALUES (%s, %s, %s, %s, %s, %s::vector, %s, %s, %s, %s, %s, NOW(), NOW())
    ON CONFLICT (chunk_id) DO UPDATE SET
        corpus_id = EXCLUDED.corpus_id,
        content = EXCLUDED.content,
        embedding = EXCLUDED.embedding,
        embedding_dim = EXCLUDED.embedding_dim,
        doc_path = EXCLUDED.doc_path,
        metadata = EXCLUDED.metadata,
        updated_at = NOW()
"""


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key, "")
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def get_embeddings_batch(
    texts: list[str],
    *,
    url: str,
    model: str,
) -> list[list[float] | None]:
    """Batch embed через /api/embed (быстрее, чем N×/api/embeddings)."""
    import requests

    if not texts:
        return []
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        _thread_local.session = session
    payload = {
        "model": model,
        "input": [t[:8000] for t in texts],
        "truncate": True,
        "keep_alive": "24h",
    }
    try:
        r = session.post(
            f"{url.rstrip('/')}/api/embed",
            json=payload,
            timeout=300,
        )
        r.raise_for_status()
        data = r.json()
        vectors = data.get("embeddings") or []
        if len(vectors) != len(texts):
            print(f"  embed batch size mismatch: {len(vectors)} != {len(texts)}")
            return [None] * len(texts)
        return vectors
    except Exception as exc:
        print(f"  embed batch error: {exc} — fallback single")
        return [get_embedding(t, url=url, model=model) for t in texts]


def init_db(conn: Any, *, dim: int) -> None:
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            corpus_id TEXT,
            doc_id TEXT,
            doc_path TEXT,
            content TEXT,
            embedding vector(%s),
            embedding_dim INTEGER,
            page INTEGER,
            section TEXT,
            has_table BOOLEAN DEFAULT FALSE,
            metadata JSONB,
            indexed_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """,
        (dim,),
    )
    conn.commit()
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'chunks' AND column_name = 'corpus_id'
        """
    )
    if cur.fetchone() is None:
        cur.execute("ALTER TABLE chunks ADD COLUMN corpus_id TEXT")
        conn.commit()
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunks_corpus ON chunks (corpus_id)"
    )
    cur.execute(
        "UPDATE chunks SET corpus_id = 'test_docs' WHERE corpus_id IS NULL"
    )
    conn.commit()
    cur.close()


def get_embedding(text: str, *, url: str, model: str) -> list[float] | None:
    import requests

    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        _thread_local.session = session
    try:
        r = session.post(
            f"{url.rstrip('/')}/api/embeddings",
            json={"model": model, "prompt": text[:8000]},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["embedding"]
    except Exception as exc:
        print(f"  embed error: {exc}")
        return None


def load_state() -> dict[str, Any]:
    path = _active_state_path
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"offset": 0, "loaded": 0, "skipped": 0}


def save_state(state: dict[str, Any]) -> None:
    path = _active_state_path
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _pg_text(value: str | None) -> str:
    """PostgreSQL text не допускает NUL (0x00) в литералах psycopg2."""
    if not value:
        return ""
    return value.replace("\x00", "")


@dataclass
class PreparedRow:
    slice_index: int
    chunk_id: str
    doc_id: str
    doc_path: str
    text: str
    page: int
    section: str | None
    metadata: dict[str, Any]


def _prepare_row(
    chunk: dict[str, Any],
    *,
    slice_index: int,
    archive: str,
    corpus: str,
    min_chars: int,
) -> PreparedRow | None:
    text = _pg_text((chunk.get("content_preview") or "").strip())
    if len(text) < min_chars:
        return None
    rel = _pg_text((chunk.get("source_relative_path") or "").replace("\\", "/"))
    chunk_id = chunk.get("chunk_id") or hashlib.md5(f"{rel}:{text[:80]}".encode()).hexdigest()[:16]
    doc_id = _pg_text(chunk.get("doc_id") or os.path.basename(rel))
    doc_path = _pg_text(str(Path(archive) / rel) if rel else doc_id)
    metadata = {
        "corpus_id": corpus,
        "source_relative_path": rel,
        "company_id": chunk.get("company_id"),
        "project_id": chunk.get("project_id"),
        "department_id": chunk.get("department_id"),
        "classification": chunk.get("classification"),
    }
    return PreparedRow(
        slice_index=slice_index,
        chunk_id=chunk_id,
        doc_id=doc_id,
        doc_path=doc_path,
        text=text,
        page=int(chunk.get("page") or 0),
        section=_pg_text(chunk.get("section")),
        metadata=metadata,
    )


def _embed_parallel(
    rows: list[PreparedRow],
    *,
    url: str,
    model: str,
    workers: int,
) -> list[tuple[PreparedRow, list[float] | None]]:
    if workers <= 1 or len(rows) <= 1:
        return [(row, get_embedding(row.text, url=url, model=model)) for row in rows]

    out: list[tuple[PreparedRow, list[float] | None]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(get_embedding, row.text, url=url, model=model): row
            for row in rows
        }
        for fut in as_completed(futures):
            row = futures[fut]
            try:
                out.append((row, fut.result()))
            except Exception as exc:
                print(f"  embed error: {exc}")
                out.append((row, None))
    order = {row.slice_index: (row, emb) for row, emb in out}
    return [order[row.slice_index] for row in rows if row.slice_index in order]


def _insert_rows(
    cur: Any,
    rows: list[tuple[PreparedRow, list[float]]],
    *,
    corpus: str,
    dim: int,
) -> None:
    from psycopg2.extras import execute_batch

    params = []
    for row, embedding in rows:
        emb_str = "[" + ",".join(str(float(x)) for x in embedding) + "]"
        params.append(
            (
                row.chunk_id,
                corpus,
                row.doc_id,
                row.doc_path,
                row.text,
                emb_str,
                dim,
                row.page,
                row.section,
                False,
                json.dumps(row.metadata, ensure_ascii=False),
            )
        )
    execute_batch(cur, INSERT_SQL, params, page_size=min(64, len(params)))


def main() -> int:
    parser = argparse.ArgumentParser(description="chunks-v2 → PostgreSQL chunks (Ollama 768)")
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_V2)
    parser.add_argument("--corpus", default="skru-2")
    parser.add_argument("--limit", type=int, default=0, help="Макс. чанков за запуск (0 = все)")
    parser.add_argument("--batch", type=int, default=400, help="Коммит/state каждые N загруженных чанков")
    parser.add_argument(
        "--embed-batch",
        type=int,
        default=_env_int("TMKI_EMBED_BATCH", 48),
        help="Чанков за один вызов /api/embed (default: 48)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=_env_int("TMKI_LOAD_WORKERS", 8),
        help="Устар.: параллельных /api/embeddings (fallback). Основной путь — --embed-batch",
    )
    parser.add_argument("--resume", action="store_true", help="Продолжить с offset из state")
    parser.add_argument("--replace-corpus", action="store_true", help="DELETE WHERE corpus_id=...")
    parser.add_argument("--min-chars", type=int, default=40, help="Пропускать слишком короткий текст")
    args = parser.parse_args()
    workers = max(1, args.workers)
    embed_batch = max(1, args.embed_batch)
    set_state_path(state_path_for(args.corpus))

    if not args.chunks.is_file():
        print(f"Нет файла: {args.chunks}")
        print("Сначала: cd runtime && python scripts/reindex_regulations_local.py --corpus skru-2")
        return 1

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("DATABASE_URL не задан (config/rag_config.env)")
        return 1

    ollama = os.environ.get("OLLAMA_URL") or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
    model = os.environ.get("OLLAMA_EMBEDDING_MODEL") or os.environ.get("TMKI_EMBEDDING_MODEL") or "nomic-embed-text"
    dim = _env_int("TMKI_EMBEDDING_DIMS", _env_int("TMKI_EMBEDDING_DIM", 768))
    archive = os.environ.get("TMKI_REGULATIONS_ARCHIVE", r"D:\Курсор\СКРУ-2")

    import psycopg2
    from tqdm import tqdm

    from tmki_rag.chunks_io import load_chunks_file

    print("=" * 60)
    print("load_skru2_to_chunks")
    print(f"  source: {args.chunks}")
    print(f"  corpus: {args.corpus}")
    print(f"  dim: {dim}  model: {model}")
    print(f"  embed-batch: {embed_batch}  commit every: {args.batch}  (workers fallback: {workers})")
    print("=" * 60)

    all_chunks = load_chunks_file(args.chunks)
    total = len(all_chunks)
    print(f"chunks-v2: {total} записей")

    state = load_state() if args.resume else {"offset": 0, "loaded": 0, "skipped": 0}
    state["corpus_id"] = args.corpus
    offset = int(state.get("offset") or 0)
    if not args.resume:
        offset = 0
        state = {"offset": 0, "loaded": 0, "skipped": 0}

    end = total
    if args.limit > 0:
        end = min(total, offset + args.limit)

    conn = psycopg2.connect(db_url)
    init_db(conn, dim=dim)
    cur = conn.cursor()

    if args.replace_corpus:
        cur.execute("DELETE FROM chunks WHERE corpus_id = %s", (args.corpus,))
        conn.commit()
        print(f"Удалены строки corpus_id={args.corpus}")

    loaded_run = 0
    skipped_run = 0
    last_commit_bucket = 0
    t0 = time.time()
    slice_chunks = all_chunks[offset:end]
    slice_len = len(slice_chunks)
    i = 0

    pbar = tqdm(total=slice_len, desc="embed+load")

    while i < slice_len:
        batch_rows: list[PreparedRow] = []
        batch_start = i
        while len(batch_rows) < embed_batch and i < slice_len:
            row = _prepare_row(
                slice_chunks[i],
                slice_index=i,
                archive=archive,
                corpus=args.corpus,
                min_chars=args.min_chars,
            )
            if row is None:
                skipped_run += 1
            else:
                batch_rows.append(row)
            i += 1

        if not batch_rows:
            pbar.update(i - batch_start)
            continue

        texts = [row.text for row in batch_rows]
        vectors = get_embeddings_batch(texts, url=ollama, model=model)
        ok_rows: list[tuple[PreparedRow, list[float]]] = []
        for row, embedding in zip(batch_rows, vectors):
            if embedding is None:
                skipped_run += 1
                continue
            ok_rows.append((row, embedding))

        if ok_rows:
            _insert_rows(cur, ok_rows, corpus=args.corpus, dim=dim)
            loaded_run += len(ok_rows)
            bucket = loaded_run // args.batch
            if bucket > last_commit_bucket:
                conn.commit()
                state["offset"] = offset + i
                state["embed_batch"] = embed_batch
                state["workers"] = workers
                save_state(state)
                last_commit_bucket = bucket

        pbar.update(i - batch_start)

    pbar.close()
    conn.commit()
    state["offset"] = end
    state["embed_batch"] = embed_batch
    state["workers"] = workers
    save_state(state)

    cur.execute(
        "SELECT corpus_id, COUNT(*) FROM chunks GROUP BY corpus_id ORDER BY COUNT(*) DESC"
    )
    print("\nТаблица chunks:")
    for row in cur.fetchall():
        print(f"  {row[0] or '(null)'}: {row[1]}")

    cur.close()
    conn.close()
    elapsed = round(time.time() - t0, 1)
    rate = round(loaded_run / elapsed, 2) if elapsed > 0 else 0
    print(f"\nГотово за {elapsed}s ({rate} чанк/с). offset={end}/{total}. state: {_active_state_path}")
    if end >= total:
        pause_path = RUNTIME / "artifacts" / "demo" / "demo-paused.json"
        if pause_path.is_file():
            try:
                pause_path.unlink()
                print("Demo: пауза снята — можно запустить .\\start-demo.ps1")
            except OSError:
                pass
    if end < total:
        print(
            f"Продолжить: python scripts/load_skru2_to_chunks.py --resume --embed-batch {embed_batch}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
