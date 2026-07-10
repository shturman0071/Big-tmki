# -*- coding: utf-8 -*-
"""Исправить пути ВКС в PG/state и убедиться, что файлы в каталоге skru-2."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME))
sys.path.insert(0, str(RUNTIME.parent))

from tmki_runtime.rag_env import load_rag_config

load_rag_config(override=False)


def main() -> int:
    import psycopg2

    archive = Path(os.environ.get("TMKI_REGULATIONS_ARCHIVE", r"D:\Курсор\СКРУ-2"))
    vks_dir = None
    for p in archive.iterdir():
        if p.is_dir() and p.name.lower() == "вкс":
            vks_dir = p
            break
    if vks_dir is None:
        print("Папка ВКС не найдена в архиве")
        return 1

    files = {f.name: f for f in vks_dir.iterdir() if f.is_file()}
    print(f"VKS folder: {vks_dir} files={len(files)}")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute(
        """
        SELECT chunk_id, doc_path
        FROM chunks
        WHERE corpus_id IN ('skru-2', 'vks')
          AND (
            metadata->>'merged_from_corpus' = 'vks'
            OR corpus_id = 'vks'
            OR doc_path ILIKE '%вкс%'
          )
        """
    )
    rows = cur.fetchall()
    updated = 0
    for chunk_id, doc_path in rows:
        name = Path(str(doc_path)).name
        target = files.get(name)
        if target is None:
            # try fuzzy: path already correct
            if Path(str(doc_path)).is_file():
                continue
            print(" missing file for", name)
            continue
        new_path = str(target)
        if new_path != str(doc_path):
            cur.execute(
                "UPDATE chunks SET doc_path = %s, updated_at = NOW() WHERE chunk_id = %s",
                (new_path, chunk_id),
            )
            updated += 1
    conn.commit()
    print(f"updated doc_path rows: {updated}")

    # Fix reindex-state processed entries
    state_path = RUNTIME / "artifacts" / "regulations-import" / "reindex-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    processed = list(state.get("processed") or [])
    # drop bad bare filenames we added
    bare_names = set(files.keys())
    cleaned = []
    for p in processed:
        name = Path(p).name
        # remove mistaken entries like "ВКС (1).docx" without folder
        if p.replace("\\", "/") == name and name in bare_names:
            continue
        cleaned.append(p)
    known = set(cleaned)
    added = 0
    for name, full in sorted(files.items()):
        rel = str(full.relative_to(archive)).replace("\\", "/")
        if rel not in known:
            cleaned.append(rel)
            known.add(rel)
            added += 1
    state["processed"] = cleaned
    state["vks_merged_into_skru2"] = True
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"state: +{added} correct VKS paths, processed={len(cleaned)}")

    cur.execute(
        """
        SELECT COUNT(*), COUNT(DISTINCT doc_path)
        FROM chunks
        WHERE corpus_id = 'skru-2'
          AND doc_path ILIKE '%\\ВКС\\%'
        """
    )
    print("skru-2 paths with \\ВКС\\:", cur.fetchone())
    # also forward slash / unicode
    cur.execute(
        """
        SELECT COUNT(DISTINCT doc_path) FROM chunks
        WHERE corpus_id='skru-2' AND metadata->>'merged_from_corpus'='vks'
        """
    )
    print("skru-2 merged distinct docs:", cur.fetchone()[0])
    cur.execute(
        "SELECT DISTINCT doc_path FROM chunks WHERE corpus_id='skru-2' AND metadata->>'merged_from_corpus'='vks'"
    )
    for (p,) in cur.fetchall():
        print(" ", p)
        print("   exists", Path(p).is_file())

    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
