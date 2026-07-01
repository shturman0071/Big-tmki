from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from tmki_ingest.chunking import build_chunks_from_ocr
from tmki_ingest.dedup import DedupResult, DedupStore, check_dedup, compute_content_hash, dedup_key
from tmki_ingest.gate import validate_ingest
from tmki_ocr import run_ocr
from tmki_rag.folders import FolderAclContext, resolve_folder_id
from tmki_rag.index import ChunkIndex


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class DocumentPipelineResult:
    ingest_response: dict[str, Any]
    ocr_result: dict[str, Any] | None = None
    chunks: list[dict[str, Any]] | None = None


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


def _ingest_response(
    request: dict[str, Any],
    accept: IngestAcceptResult,
) -> dict[str, Any]:
    trace_id = request["trace_id"]
    policy_context = request["policy_context"]
    resp: dict[str, Any] = {
        "schema_version": "0.1",
        "trace_id": trace_id,
        "ingest_status": accept.ingest_status,
        "content_hash": accept.content_hash or "sha256:" + "0" * 64,
        "occurred_at": _now_iso(),
    }
    if accept.doc_id:
        resp["doc_id"] = accept.doc_id
    if accept.content_hash:
        resp["content_hash"] = accept.content_hash
        resp["dedup"] = {
            "is_duplicate": accept.ingest_status == "duplicate",
            "dedup_key": dedup_key(
                policy_context["company_id"],
                policy_context["project_id"],
                accept.content_hash,
            ),
            "action": accept.dedup_action,
        }
        if accept.ingest_status == "duplicate":
            resp["dedup"]["matched_doc_id"] = accept.doc_id
    if accept.error_code:
        resp["error"] = {"code": accept.error_code, "message": accept.error_code}
    return resp


def process_document(
    request: dict[str, Any],
    *,
    folder_acl: FolderAclContext,
    dedup_store: DedupStore,
    raw_bytes: bytes | None = None,
    mineru_mode: str = "ok",
) -> DocumentPipelineResult:
    """Ingest → OCR (stub) → chunking (MVP)."""
    accept = accept_ingest(
        request,
        folder_acl=folder_acl,
        dedup_store=dedup_store,
        raw_bytes=raw_bytes,
    )
    ingest_response = _ingest_response(request, accept)

    if accept.ingest_status in ("rejected", "duplicate"):
        return DocumentPipelineResult(ingest_response=ingest_response)

    file_meta = request.get("file", {})
    if raw_bytes is None:
        raw_bytes = base64.b64decode(file_meta.get("content_base64", ""))

    ocr_result = run_ocr(
        doc_id=accept.doc_id or "doc_unknown",
        trace_id=request["trace_id"],
        raw_bytes=raw_bytes,
        mineru_mode=mineru_mode,
    )
    markdown = ocr_result.pop("_markdown", "")

    chunks = None
    if ocr_result.get("ocr_status") == "completed" and markdown:
        policy_context = request["policy_context"]
        chunks = build_chunks_from_ocr(
            ocr_result,
            company_id=policy_context["company_id"],
            project_id=policy_context["project_id"],
            department_id=policy_context.get("department_id"),
            folder_id=accept.folder_id,
            classification=request["classification"],
            markdown=markdown,
        )
        ingest_response["ingest_status"] = "processing"
        ingest_response["job_id"] = f"job_{accept.doc_id}"

    return DocumentPipelineResult(
        ingest_response=ingest_response,
        ocr_result=ocr_result,
        chunks=chunks,
    )


def ingest_and_index(
    request: dict[str, Any],
    index: ChunkIndex,
    *,
    folder_acl: FolderAclContext,
    dedup_store: DedupStore,
    raw_bytes: bytes | None = None,
    mineru_mode: str = "ok",
) -> DocumentPipelineResult:
    """Ingest → OCR → добавить chunks в ChunkIndex."""
    result = process_document(
        request,
        folder_acl=folder_acl,
        dedup_store=dedup_store,
        raw_bytes=raw_bytes,
        mineru_mode=mineru_mode,
    )
    if result.chunks:
        index.add(result.chunks)
    return result
