from __future__ import annotations

from typing import Any, Literal

DocumentType = Literal["contract", "instruction", "report", "letter", "regulation", "other"]
LawCheckMode = Literal["never", "on_user_request", "always"]


def resolve_external_law_check(
    document_type: DocumentType,
    *,
    user_requested_law_check: bool = False,
) -> LawCheckMode:
    """
    Политика v0.3: договор — всегда; прочие новые — только по запросу пользователя.
    """
    if document_type == "contract":
        return "always"
    if user_requested_law_check:
        return "on_user_request"
    return "never"


def validate_document_creation_policy(policy: dict[str, Any]) -> dict[str, Any]:
    """Нормализует policy и проверяет обязательные правила."""
    doc_type = policy.get("document_type", "other")
    user_req = bool(policy.get("user_requested_law_check", False))
    external = resolve_external_law_check(doc_type, user_requested_law_check=user_req)
    if not policy.get("use_internal_templates", True):
        raise ValueError("use_internal_templates MUST be true")
    return {
        **policy,
        "external_law_check": external,
        "use_internal_templates": True,
    }
