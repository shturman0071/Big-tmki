import base64
from datetime import date
from pathlib import Path

from tmki_ingest import DedupStore, ingest_and_index
from tmki_rag import ChunkIndex, FolderAclContext, load_folder_catalog, load_folder_grants, rag_search

ROOT = Path(__file__).resolve().parents[2]


def _folder_acl():
    return FolderAclContext.from_catalog(
        load_folder_catalog(ROOT / "schemas/document/examples/satimol-folders.example.json"),
        load_folder_grants(ROOT / "schemas/org/examples/satimol-folder-grants.example.json"),
        as_of=date(2025, 9, 10),
    )


def test_ingest_and_index_then_rag():
    raw = "новый документ маркшейдерская съёмка участка".encode("utf-8")
    index = ChunkIndex()
    request = {
        "schema_version": "0.1",
        "trace_id": "00000000-0000-4000-8000-000000000020",
        "policy_context": {
            "company_id": "company_tmki_ru",
            "project_id": "project_satimol",
            "department_id": "dept_markscheider",
            "project_role": "Chefmarkscheider",
            "employee_id": "emp_litovsky_d",
            "clearance": "restricted",
            "env": "production",
        },
        "classification": "restricted",
        "folder_id": "folder_ms_open",
        "file": {"content_base64": base64.b64encode(raw).decode("ascii")},
    }
    result = ingest_and_index(
        request,
        index,
        folder_acl=_folder_acl(),
        dedup_store=DedupStore(),
        raw_bytes=raw,
    )
    assert result.chunks is not None
    assert len(index.list()) == 1

    resp = rag_search(
        {
            "trace_id": "t-rag",
            "query": "маркшейдерская съёмка",
            "policy_context": request["policy_context"],
        },
        index.list(),
        folder_acl=_folder_acl(),
    )
    assert len(resp["results"]) >= 1
