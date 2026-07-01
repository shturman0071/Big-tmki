from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tmki_rag.clearance import classification_meets_minimum, clearance_allows
from tmki_rag.folders import FolderAclContext, resolve_folder_id


@dataclass(frozen=True)
class IngestGateResult:
    allowed: bool
    folder_id: str | None = None
    resolved_from_path: bool = False
    error_code: str | None = None


def _folder_list(folder_acl: FolderAclContext) -> list[dict[str, Any]]:
    return list(folder_acl.folders_by_id.values())


def _resolve_folder(
    folder_acl: FolderAclContext,
    *,
    source_path: str | None,
    folder_id: str | None,
) -> tuple[str | None, bool]:
    if folder_id:
        return folder_id, False
    if source_path:
        resolved = resolve_folder_id(source_path, _folder_list(folder_acl))
        return resolved, resolved is not None
    return None, False


def validate_ingest(
    policy_context: dict[str, Any],
    classification: str,
    folder_acl: FolderAclContext,
    *,
    source_path: str | None = None,
    folder_id: str | None = None,
) -> IngestGateResult:
    """
  Проверка upload/ingest до OCR pipeline.
  Контракт ошибок: 09_document_processing.md (INGEST_*).
    """
    user_clearance = policy_context.get("clearance", "internal")
    if not clearance_allows(classification, user_clearance):
        return IngestGateResult(allowed=False, error_code="INGEST_CLEARANCE_DENIED")

    resolved_id, from_path = _resolve_folder(
        folder_acl, source_path=source_path, folder_id=folder_id
    )
    if not resolved_id:
        return IngestGateResult(
            allowed=False,
            error_code="INGEST_FOLDER_DENIED",
            resolved_from_path=from_path,
        )

    folder = folder_acl.folders_by_id.get(resolved_id)
    if not folder:
        return IngestGateResult(allowed=False, folder_id=resolved_id, error_code="INGEST_FOLDER_DENIED")

    if folder.get("company_id") != policy_context.get("company_id"):
        return IngestGateResult(allowed=False, folder_id=resolved_id, error_code="INGEST_FOLDER_DENIED")
    if folder.get("project_id") != policy_context.get("project_id"):
        return IngestGateResult(allowed=False, folder_id=resolved_id, error_code="INGEST_FOLDER_DENIED")

    folder_min = folder.get("default_classification", "internal")
    if not clearance_allows(folder_min, user_clearance):
        return IngestGateResult(allowed=False, folder_id=resolved_id, error_code="INGEST_CLEARANCE_DENIED")
    if not classification_meets_minimum(classification, folder_min):
        return IngestGateResult(allowed=False, folder_id=resolved_id, error_code="INGEST_FOLDER_DENIED")

    if not folder_acl.allows_write(resolved_id, policy_context):
        return IngestGateResult(allowed=False, folder_id=resolved_id, error_code="INGEST_FOLDER_DENIED")

    return IngestGateResult(
        allowed=True,
        folder_id=resolved_id,
        resolved_from_path=from_path,
    )


def validate_delete(
    policy_context: dict[str, Any],
    folder_acl: FolderAclContext,
    *,
    source_path: str | None = None,
    folder_id: str | None = None,
) -> IngestGateResult:
    resolved_id, from_path = _resolve_folder(
        folder_acl, source_path=source_path, folder_id=folder_id
    )
    if not resolved_id:
        return IngestGateResult(
            allowed=False,
            error_code="INGEST_FOLDER_DENIED",
            resolved_from_path=from_path,
        )

    if not folder_acl.allows_delete(resolved_id, policy_context):
        return IngestGateResult(
            allowed=False,
            folder_id=resolved_id,
            error_code="INGEST_DELETE_DENIED",
        )

    return IngestGateResult(
        allowed=True,
        folder_id=resolved_id,
        resolved_from_path=from_path,
    )
