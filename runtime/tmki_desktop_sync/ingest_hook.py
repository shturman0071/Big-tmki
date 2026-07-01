from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from tmki_ingest import DedupStore, ingest_and_index
from tmki_policy import build_policy_context, load_org_snapshot
from tmki_rag import ChunkIndex, FolderAclContext, load_folder_catalog, load_folder_grants

ROOT = Path(__file__).resolve().parents[2]


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


def ingest_synced_file(
    server_path: Path,
    *,
    policy_context: dict[str, Any] | None = None,
    folder_id: str = "folder_ms_open",
    index: ChunkIndex | None = None,
    dedup_store: DedupStore | None = None,
) -> dict[str, Any]:
    """Ingest одного файла после desktop sync (#45 → RAG)."""
    ctx = policy_context or _default_policy_context()
    acl = _default_folder_acl()
    idx = index or ChunkIndex()
    dedup = dedup_store or DedupStore()
    raw = server_path.read_bytes()
    request = {
        "schema_version": "0.1",
        "trace_id": "desktop-sync",
        "policy_context": ctx,
        "classification": "restricted",
        "folder_id": folder_id,
        "source_path": str(server_path),
        "file_name": server_path.name,
        "mime_type": "application/octet-stream",
    }
    result = ingest_and_index(
        request,
        idx,
        folder_acl=acl,
        dedup_store=dedup,
        raw_bytes=raw,
    )
    return {
        "path": str(server_path),
        "ingest_status": result.ingest_response.get("ingest_status"),
        "doc_id": result.ingest_response.get("doc_id"),
        "chunks": len(result.chunks or []),
    }
