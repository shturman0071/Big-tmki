from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

from tmki_ingest import DedupStore, ingest_and_index
from tmki_legal.corpus import load_legal_corpus_catalog
from tmki_legal.curator import DEFAULT_STATE_DIR
from tmki_policy import build_policy_context, load_org_snapshot
from tmki_rag import ChunkIndex, FolderAclContext, load_folder_catalog, load_folder_grants

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAX_BYTES = 5_000_000


def _default_policy_context() -> dict[str, Any]:
    snapshot = load_org_snapshot(ROOT / "schemas/org/examples/satimol-snapshot.example.json")
    return build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )


def _default_folder_acl() -> FolderAclContext:
    return FolderAclContext.from_catalog(
        load_folder_catalog(ROOT / "schemas/document/examples/satimol-folders.example.json"),
        load_folder_grants(ROOT / "schemas/org/examples/satimol-folder-grants.example.json"),
        as_of=date(2025, 9, 10),
    )


def _catalog_doc_by_key(catalog_path: Path | None = None) -> dict[str, dict[str, Any]]:
    catalog = load_legal_corpus_catalog(catalog_path)
    out: dict[str, dict[str, Any]] = {}
    for category in catalog.get("categories", []):
        for doc in category.get("documents", []):
            out[doc["doc_key"]] = doc
    return out


def fetch_legal_source(url: str, *, max_bytes: int = DEFAULT_MAX_BYTES, timeout: float = 30.0) -> bytes:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "tmki-legal-ingest/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(max_bytes + 1)[:max_bytes]


def ingest_legal_update(
    update: dict[str, Any],
    *,
    doc: dict[str, Any] | None = None,
    policy_context: dict[str, Any] | None = None,
    folder_id: str = "folder_ms_open",
    index: ChunkIndex | None = None,
    dedup_store: DedupStore | None = None,
    fetcher: Any = None,
) -> dict[str, Any]:
    """Ingest одной regulatory-update записи (URL → OCR → chunks)."""
    url = update.get("source_url")
    if not url:
        return {"doc_key": update.get("doc_key"), "ingest_status": "failed", "error": "missing_source_url"}

    ctx = policy_context or _default_policy_context()
    acl = _default_folder_acl()
    idx = index or ChunkIndex()
    dedup = dedup_store or DedupStore()
    doc_key = update["doc_key"]
    title = (doc or {}).get("title") or update.get("title") or doc_key

    try:
        raw = (fetcher or fetch_legal_source)(url)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"doc_key": doc_key, "ingest_status": "failed", "error": str(exc)}

    request = {
        "schema_version": "0.1",
        "trace_id": f"legal-{doc_key}-{uuid4().hex[:8]}",
        "policy_context": ctx,
        "classification": "restricted",
        "folder_id": folder_id,
        "provenance": {
            "source": "legal_corpus",
            "doc_key": doc_key,
            "source_url": url,
            "title": title,
        },
        "file_name": f"{doc_key}.html",
        "mime_type": "text/html",
    }
    result = ingest_and_index(request, idx, folder_acl=acl, dedup_store=dedup, raw_bytes=raw)
    status = result.ingest_response.get("ingest_status", "failed")
    out: dict[str, Any] = {
        "doc_key": doc_key,
        "ingest_status": "ingested" if status in ("processing", "accepted") else status,
        "doc_id": result.ingest_response.get("doc_id"),
        "chunks": len(result.chunks or []),
    }
    if status in ("rejected", "duplicate") or result.ingest_response.get("error"):
        out["ingest_status"] = "failed"
        out["error"] = (result.ingest_response.get("error") or {}).get("code", status)
    return out


def apply_pending_legal_updates(
    *,
    state_dir: Path | None = None,
    catalog_path: Path | None = None,
    index: ChunkIndex | None = None,
    dedup_store: DedupStore | None = None,
    dry_run: bool = False,
    fetcher: Any = None,
) -> dict[str, Any]:
    """Применить pending записи из regulatory-updates.json к ingest pipeline."""
    out_dir = state_dir or DEFAULT_STATE_DIR
    updates_file = out_dir / "regulatory-updates.json"
    if not updates_file.is_file():
        return {"pending": 0, "applied": 0, "failed": 0, "results": [], "updates_path": None}

    payload = json.loads(updates_file.read_text(encoding="utf-8"))
    updates: list[dict[str, Any]] = list(payload.get("updates") or [])
    pending = [u for u in updates if u.get("ingest_status") == "pending"]
    if not pending:
        return {"pending": 0, "applied": 0, "failed": 0, "results": [], "updates_path": str(updates_file)}

    docs_by_key = _catalog_doc_by_key(catalog_path)
    idx = index or ChunkIndex()
    dedup = dedup_store or DedupStore()
    results: list[dict[str, Any]] = []
    applied = 0
    failed = 0

    for update in pending:
        if dry_run:
            results.append({"doc_key": update["doc_key"], "ingest_status": "pending", "dry_run": True})
            continue
        row = ingest_legal_update(
            update,
            doc=docs_by_key.get(update["doc_key"]),
            index=idx,
            dedup_store=dedup,
            fetcher=fetcher,
        )
        results.append(row)
        if row.get("ingest_status") == "ingested":
            update["ingest_status"] = "ingested"
            applied += 1
        else:
            update["ingest_status"] = "failed"
            failed += 1

    if not dry_run:
        payload["updates"] = updates
        updates_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "pending": len(pending),
        "applied": applied,
        "failed": failed,
        "results": results,
        "updates_path": str(updates_file),
        "dry_run": dry_run,
    }
