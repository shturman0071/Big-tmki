import json
from datetime import date
from pathlib import Path

from tmki_policy import build_policy_context, load_org_snapshot
from tmki_rag import rag_search

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "schemas/org/examples/satimol-snapshot.example.json"
CHUNKS_FILE = ROOT / "schemas/document/examples/satimol-chunks.example.json"


def _load_chunks():
    data = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    return data["chunks"]


def _search(snapshot, employee_id, query="маркшейдерская съёмка"):
    ctx = build_policy_context(
        snapshot,
        employee_id=employee_id,
        env="production",
        as_of=date(2025, 9, 10),
    )
    request = {
        "schema_version": "0.1",
        "trace_id": "trace-test-rag",
        "query": query,
        "top_k": 8,
        "policy_context": ctx,
    }
    return rag_search(request, _load_chunks())


def test_chefmarkscheider_rls_dept_and_clearance():
    snapshot = load_org_snapshot(SNAPSHOT)
    resp = _search(snapshot, "emp_litovsky_d")
    doc_ids = {r["doc_id"] for r in resp["results"]}

    assert not resp.get("denied_by_policy")
    assert resp["filter_applied"]["department_scope"] == "S_dept"
    assert "doc_markscheider_ks_2025" in doc_ids
    assert "doc_pto_schedule" not in doc_ids
    assert "doc_hr_payroll" not in doc_ids
    assert "doc_satimol_grd" not in doc_ids
    assert resp["stats"]["results_after_rls"] == 1


def test_projektleiter_sees_project_scope():
    snapshot = load_org_snapshot(SNAPSHOT)
    resp = _search(snapshot, "emp_neff_a")
    doc_ids = {r["doc_id"] for r in resp["results"]}

    assert resp["filter_applied"]["department_scope"] == "S_project"
    assert "doc_markscheider_ks_2025" in doc_ids
    assert "doc_pto_schedule" in doc_ids
    assert "doc_satimol_grd" in doc_ids
    assert "doc_hr_payroll" not in doc_ids


def test_denied_when_s_dept_without_department():
    chunks = _load_chunks()
    request = {
        "schema_version": "0.1",
        "trace_id": "trace-denied",
        "query": "маркшейдерская",
        "top_k": 5,
        "policy_context": {
            "company_id": "company_tmki_ru",
            "project_id": "project_satimol",
            "project_role": "Chefmarkscheider",
            "employee_id": "emp_x",
            "clearance": "restricted",
            "env": "production",
        },
    }
    resp = rag_search(request, chunks)
    assert resp["denied_by_policy"] is True
    assert resp["results"] == []
