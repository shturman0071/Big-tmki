from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


def compute_content_hash(raw_bytes: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw_bytes).hexdigest()


def dedup_key(company_id: str, project_id: str, content_hash: str) -> str:
    return f"{company_id}:{project_id}:{content_hash}"


@dataclass
class DedupRecord:
    doc_id: str
    classification: str
    content_hash: str
    idempotency_key: str | None = None


@dataclass
class DedupStore:
    """In-memory dedup index (MVP); production — Postgres/Redis."""

    records: dict[str, DedupRecord] = field(default_factory=dict)
    idempotency: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class DedupResult:
    ingest_status: str
    dedup_action: str
    doc_id: str | None = None
    matched_doc_id: str | None = None
    warning: str | None = None


def check_dedup(
    store: DedupStore,
    *,
    company_id: str,
    project_id: str,
    content_hash: str,
    classification: str,
    idempotency_key: str | None = None,
    force_reprocess: bool = False,
    new_doc_id: str | None = None,
) -> DedupResult:
    key = dedup_key(company_id, project_id, content_hash)

    if idempotency_key and idempotency_key in store.idempotency:
        cached = store.idempotency[idempotency_key]
        return DedupResult(
            ingest_status=cached["ingest_status"],
            dedup_action="skipped_processing",
            doc_id=cached.get("doc_id"),
            matched_doc_id=cached.get("matched_doc_id"),
        )

    existing = store.records.get(key)
    if existing and not force_reprocess:
        if existing.classification == classification:
            result = DedupResult(
                ingest_status="duplicate",
                dedup_action="skipped_processing",
                matched_doc_id=existing.doc_id,
            )
        else:
            result = DedupResult(
                ingest_status="duplicate",
                dedup_action="linked_existing",
                matched_doc_id=existing.doc_id,
                warning="classification differs from existing document",
            )
        if idempotency_key:
            store.idempotency[idempotency_key] = {
                "ingest_status": result.ingest_status,
                "matched_doc_id": result.matched_doc_id,
            }
        return result

    doc_id = new_doc_id or f"doc_{content_hash[7:19]}"
    store.records[key] = DedupRecord(
        doc_id=doc_id,
        classification=classification,
        content_hash=content_hash,
        idempotency_key=idempotency_key,
    )
    action = "reprocessed" if existing and force_reprocess else "none"
    result = DedupResult(
        ingest_status="accepted",
        dedup_action=action,
        doc_id=doc_id,
    )
    if idempotency_key:
        store.idempotency[idempotency_key] = {
            "ingest_status": result.ingest_status,
            "doc_id": doc_id,
        }
    return result
