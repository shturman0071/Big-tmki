from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tmki_legal.corpus import iter_catalog_documents, load_legal_corpus_catalog, probe_document_sources

DEFAULT_STATE_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "legal-corpus"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fingerprint_key(probe: dict[str, Any] | None) -> str | None:
    if not probe:
        return None
    if probe.get("content_hash"):
        return str(probe["content_hash"])
    parts = [str(probe.get("etag") or ""), str(probe.get("last_modified") or ""), str(probe.get("status") or "")]
    joined = "|".join(parts)
    return joined if any(parts) else None


def run_legal_corpus_curator(
    *,
    catalog_path: Path | None = None,
    state_dir: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Еженедельная проверка каталога внешней нормативной базы.
    Сравнивает fingerprint источников; при изменении — regulatory-update record.
    """
    catalog = load_legal_corpus_catalog(catalog_path)
    out_dir = state_dir or DEFAULT_STATE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    state_file = out_dir / "curator-state.json"
    updates_file = out_dir / "regulatory-updates.json"

    state = {"documents": {}}
    if state_file.is_file():
        state = json.loads(state_file.read_text(encoding="utf-8"))

    updates: list[dict[str, Any]] = []
    checked = 0
    changed = 0
    errors = 0

    for doc in iter_catalog_documents(catalog):
        checked += 1
        doc_key = doc["doc_key"]
        result = probe_document_sources(doc)
        fp = _fingerprint_key(result.get("primary"))
        prev = (state.get("documents") or {}).get(doc_key, {})
        prev_fp = prev.get("fingerprint")

        update_type = "no_change"
        if fp is None:
            errors += 1
            update_type = "no_change"
        elif prev_fp is None:
            update_type = "new_edition"
            changed += 1
        elif prev_fp != fp:
            update_type = "amendment"
            changed += 1

        record = {
            "schema_version": "0.1",
            "doc_key": doc_key,
            "title": doc.get("title"),
            "update_type": update_type,
            "old_content_hash": prev_fp if prev_fp and prev_fp.startswith("sha256:") else None,
            "new_content_hash": fp if fp and str(fp).startswith("sha256:") else None,
            "source_url": (result.get("primary") or {}).get("url"),
            "detected_at": _now_iso(),
            "ingest_status": "pending" if update_type != "no_change" else "skipped",
            "notify_curator": update_type != "no_change",
        }
        if update_type != "no_change":
            updates.append(record)

        state.setdefault("documents", {})[doc_key] = {
            "fingerprint": fp,
            "last_checked_at": _now_iso(),
            "title": doc.get("title"),
            "probe": result.get("primary"),
        }

    if not dry_run:
        state["last_run_at"] = _now_iso()
        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        if updates:
            payload = {"schema_version": "0.1", "updates": updates, "occurred_at": _now_iso()}
            updates_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "checked": checked,
        "changed": changed,
        "errors": errors,
        "updates": updates,
        "state_path": str(state_file),
        "updates_path": str(updates_file) if updates else None,
        "dry_run": dry_run,
    }
