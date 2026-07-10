# -*- coding: utf-8 -*-
"""Скопировать чанки корпуса vks в skru-2 (без повторного embed)."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME))
sys.path.insert(0, str(RUNTIME.parent))

from tmki_runtime.rag_env import load_rag_config

load_rag_config(override=False)


def _new_chunk_id(old_id: str, doc_path: str) -> str:
    raw = f"skru2-from-vks|{old_id}|{doc_path}"
    return "skru2_vks_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]


def main() -> int:
    import psycopg2
    from psycopg2.extras import execute_batch

    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("DATABASE_URL не задан")
        return 1

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT chunk_id, doc_id, doc_path, content, embedding::text,
               embedding_dim, page, section, has_table, metadata
        FROM chunks
        WHERE corpus_id = 'vks'
        """
    )
    rows = cur.fetchall()
    print(f"vks rows: {len(rows)}")
    if not rows:
        print("Нечего копировать")
        return 0

    insert_sql = """
        INSERT INTO chunks (
            chunk_id, corpus_id, doc_id, doc_path, content, embedding,
            embedding_dim, page, section, has_table, metadata, indexed_at, updated_at
        ) VALUES (
            %s, 'skru-2', %s, %s, %s, %s::vector, %s, %s, %s, %s, %s, NOW(), NOW()
        )
        ON CONFLICT (chunk_id) DO UPDATE SET
            corpus_id = EXCLUDED.corpus_id,
            content = EXCLUDED.content,
            embedding = EXCLUDED.embedding,
            embedding_dim = EXCLUDED.embedding_dim,
            doc_path = EXCLUDED.doc_path,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
    """
    params = []
    paths: set[str] = set()
    for chunk_id, doc_id, doc_path, content, emb, dim, page, section, has_table, metadata in rows:
        new_id = _new_chunk_id(str(chunk_id), str(doc_path or ""))
        meta = metadata
        if isinstance(meta, dict):
            meta = dict(meta)
            meta["merged_from_corpus"] = "vks"
            meta["source_chunk_id"] = chunk_id
        elif meta is None:
            meta = {"merged_from_corpus": "vks", "source_chunk_id": chunk_id}
        else:
            # jsonb may already be dict via psycopg2
            try:
                meta = dict(meta)
                meta["merged_from_corpus"] = "vks"
            except Exception:
                meta = {"merged_from_corpus": "vks", "source_chunk_id": chunk_id}
        params.append(
            (
                new_id,
                doc_id,
                doc_path,
                content,
                emb,
                dim,
                page,
                section,
                has_table,
                json.dumps(meta, ensure_ascii=False) if not isinstance(meta, str) else meta,
            )
        )
        if doc_path:
            paths.add(str(doc_path))

    execute_batch(cur, insert_sql, params, page_size=50)
    conn.commit()

    cur.execute(
        """
        SELECT COUNT(*), COUNT(DISTINCT doc_path)
        FROM chunks
        WHERE corpus_id = 'skru-2'
          AND (
            doc_path ~* '(^|[/\\\\])вкс([/\\\\]|$)'
            OR metadata->>'merged_from_corpus' = 'vks'
          )
        """
    )
    print("skru-2 vks after merge:", cur.fetchone())
    cur.execute("SELECT corpus_id, COUNT(*) FROM chunks GROUP BY 1 ORDER BY 2 DESC")
    print("corpora:", cur.fetchall())
    cur.close()
    conn.close()

    # Добавить относительные пути в reindex-state.processed (для учёта)
    state_path = RUNTIME / "artifacts" / "regulations-import" / "reindex-state.json"
    archive = Path(os.environ.get("TMKI_REGULATIONS_ARCHIVE", r"D:\Курсор\СКРУ-2"))
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        processed = list(state.get("processed") or [])
        known = set(processed)
        added = 0
        for abs_path in sorted(paths):
            try:
                rel = str(Path(abs_path).resolve().relative_to(archive.resolve())).replace("\\", "/")
            except Exception:
                # уже относительный или вне архива
                rel = abs_path.replace("\\", "/")
                if "ВКС/" in rel or "вкс/" in rel.lower():
                    idx = rel.lower().find("вкс/")
                    if idx >= 0:
                        rel = rel[idx:]
                        # restore original case folder if possible
                        for part in abs_path.replace("\\", "/").split("/"):
                            if part.lower() == "вкс":
                                rel = "/".join(abs_path.replace("\\", "/").split("/")[
                                    abs_path.replace("\\", "/").lower().split("/").index("вкс") :
                                ])
                                break
            if rel not in known:
                processed.append(rel)
                known.add(rel)
                added += 1
        state["processed"] = processed
        state["vks_merged_into_skru2"] = True
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"reindex-state: +{added} paths (total processed {len(processed)})")

    print("OK: ВКС влита в skru-2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
