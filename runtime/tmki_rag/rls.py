from __future__ import annotations

from typing import Any

from tmki_rag.clearance import clearance_allows


def _department_allowed(
    chunk: dict[str, Any],
    policy_context: dict[str, Any],
    department_scope: str,
) -> bool:
    chunk_dept = chunk.get("department_id")
    user_dept = policy_context.get("department_id")

    if department_scope == "S_project":
        return True

    if department_scope == "S_dept":
        if not user_dept:
            return False
        # проектные документы без department_id доступны при S_project; для S_dept — только своё подразделение
        if chunk_dept is None:
            return False
        return chunk_dept == user_dept

    if department_scope == "S_dept_tree":
        if not user_dept:
            return False
        dept_tree = policy_context.get("dept_tree") or [user_dept]
        if chunk_dept is None:
            return False
        return chunk_dept in dept_tree

    return False


def passes_rls(
    chunk: dict[str, Any],
    policy_context: dict[str, Any],
    *,
    department_scope: str,
    extra_filters: dict[str, Any] | None = None,
) -> bool:
    """Проверка RLS-метаданных chunk до vector/BM25 ранжирования."""
    if chunk.get("company_id") != policy_context.get("company_id"):
        return False
    if chunk.get("project_id") != policy_context.get("project_id"):
        return False
    if not clearance_allows(chunk.get("classification", "internal"), policy_context.get("clearance", "internal")):
        return False

    contractor_id = policy_context.get("contractor_id")
    if contractor_id:
        chunk_contractor = chunk.get("contractor_id")
        if chunk_contractor and chunk_contractor != contractor_id:
            return False

    if not _department_allowed(chunk, policy_context, department_scope):
        return False

    if extra_filters:
        if "department_id" in extra_filters and chunk.get("department_id") != extra_filters["department_id"]:
            return False
        if "document_type" in extra_filters and chunk.get("document_type") != extra_filters["document_type"]:
            return False
        if "language" in extra_filters and chunk.get("language") != extra_filters["language"]:
            return False
        if "doc_ids" in extra_filters and chunk.get("doc_id") not in extra_filters["doc_ids"]:
            return False

    return True
