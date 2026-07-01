import os

import pytest

from tmki_sharepoint import StubSharePointAdapter, get_sharepoint_adapter
from tmki_sharepoint.graph import GraphSharePointAdapter
from tmki_sharepoint.sync import SharePointPermissionChange, build_sync_plan
from tmki_rag import load_folder_catalog, load_folder_grants
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_get_sharepoint_adapter_stub_default(monkeypatch):
    monkeypatch.delenv("AZURE_TENANT_ID", raising=False)
    monkeypatch.setenv("TMKI_SHAREPOINT_ADAPTER", "stub")
    adapter = get_sharepoint_adapter()
    assert isinstance(adapter, StubSharePointAdapter)


def test_get_sharepoint_adapter_graph_requires_env(monkeypatch):
    monkeypatch.setenv("TMKI_SHAREPOINT_ADAPTER", "graph")
    monkeypatch.delenv("AZURE_TENANT_ID", raising=False)
    with pytest.raises(RuntimeError, match="AZURE"):
        get_sharepoint_adapter()


def test_graph_build_invite_operation(monkeypatch):
    monkeypatch.setenv("TMKI_GRAPH_DRY_RUN", "1")
    adapter = GraphSharePointAdapter(
        tenant_id="t",
        client_id="c",
        client_secret="s",
        site_id="site123",
        employee_upn_map={"emp_ivanov_a": "ivanov@tmki.ru"},
    )
    change = SharePointPermissionChange(
        folder_id="folder_ms_contracts",
        physical_path="/sites/Satimol/Markscheider/Договоры",
        storage_backend="sharepoint",
        employee_id="emp_ivanov_a",
        action="add_read",
        grant_id="grant_test",
    )
    op = adapter._build_operation(change)
    assert op["steps"][0]["step"] == "resolve"
    assert op["steps"][1]["step"] == "invite"
    assert op["steps"][1]["body"]["recipients"][0]["email"] == "ivanov@tmki.ru"


def test_graph_apply_dry_run(monkeypatch):
    monkeypatch.setenv("TMKI_GRAPH_DRY_RUN", "1")
    folders = load_folder_catalog(ROOT / "schemas/document/examples/satimol-folders.example.json")
    grants = load_folder_grants(ROOT / "schemas/org/examples/satimol-folder-grants.example.json")
    adapter = GraphSharePointAdapter(
        tenant_id="t",
        client_id="c",
        client_secret="s",
        site_id="site123",
    )
    plan = build_sync_plan(grants, folders)
    result = adapter.apply(plan)
    assert result["dry_run"] is True
    assert result["changes_applied"] == len(plan)
    assert result["items"][0]["graph_status"] == "dry_run"
    assert "resolve" in result["items"][0]["steps"]


def test_graph_execute_invite_production(monkeypatch):
    monkeypatch.setenv("TMKI_GRAPH_DRY_RUN", "0")

    calls: list[tuple[str, str]] = []

    def mock_http(method, url, body, headers):
        calls.append((method, url))
        if method == "GET" and "/drive/root:" in url:
            return {
                "status_code": 200,
                "body": {"id": "item1", "parentReference": {"driveId": "drive1"}},
            }
        if method == "POST" and "/invite" in url:
            return {"status_code": 200, "body": {"value": []}}
        return {"status_code": 500, "body": {}, "error": True}

    adapter = GraphSharePointAdapter(
        tenant_id="t",
        client_id="c",
        client_secret="s",
        site_id="site123",
        employee_upn_map={"emp_ivanov_a": "ivanov@tmki.ru"},
        http_request=mock_http,
    )
    adapter._token = "fake-token"

    change = SharePointPermissionChange(
        folder_id="folder_ms_contracts",
        physical_path="/sites/Satimol/Markscheider/Договоры",
        storage_backend="sharepoint",
        employee_id="emp_ivanov_a",
        action="add_read",
        grant_id="grant_test",
    )
    result = adapter.apply([change])
    assert result["dry_run"] is False
    assert result["items"][0]["graph_status"] == "ok"
    assert any(m == "GET" for m, _ in calls)
    assert any(m == "POST" and "/invite" in u for m, u in calls)
