from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

from tmki_ingest.dedup import DedupResult, DedupStore, check_dedup, compute_content_hash
from tmki_ingest.gate import validate_ingest
from tmki_rag.folders import FolderAclContext, resolve_folder_id


@dataclass(frozen=True)
class IngestAcceptResult:
    ingest_status: str
    doc_id: str | None
    folder_id: str | None
    content_hash: str
    dedup_action: str
    error_code: str | None = None
    warning: str | None = None


def accept_ingest(
    request: dict[str, Any],
    *,
    folder_acl: FolderAclContext,
    dedup_store: DedupStore,
    raw_bytes: bytes | None = None,
) -> IngestAcceptResult:
    """
    Ingest шаг 1: gate + hash + dedup (09_document_processing.md).
    `request` — тело ingest-request (+ MAY provenance.source_path).
    """
    policy_context = request["policy_context"]
    classification = request["classification"]
    provenance = request.get("provenance") or {}
    source_path = provenance.get("source_path")
    folder_id = request.get("folder_id")

    if source_path and not folder_id:
        folder_id = resolve_folder_id(source_path, list(folder_acl.folders_by_id.values()))

    gate = validate_ingest(
        policy_context,
        classification,
        folder_acl,
        source_path=source_path,
        folder_id=folder_id,
    )
    if not gate.allowed:
        return IngestAcceptResult(
            ingest_status="rejected",
            doc_id=None,
            folder_id=gate.folder_id,
            content_hash="",
            dedup_action="none",
            error_code=gate.error_code,
        )

    file_meta = request.get("file", {})
    if raw_bytes is None:
        raw_bytes = base64.b64decode(file_meta.get("content_base64", ""))

    content_hash = compute_content_hash(raw_bytes)
    dedup: DedupResult = check_dedup(
        dedup_store,
        company_id=policy_context["company_id"],
        project_id=policy_context["project_id"],
        content_hash=content_hash,
        classification=classification,
        idempotency_key=request.get("idempotency_key"),
        force_reprocess=bool(request.get("force_reprocess")),
    )

    return IngestAcceptResult(
        ingest_status=dedup.ingest_status,
        doc_id=dedup.doc_id or dedup.matched_doc_id,
        folder_id=gate.folder_id,
        content_hash=content_hash,
        dedup_action=dedup.dedup_action,
        warning=dedup.warning,
    )
