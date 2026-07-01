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
    assert op["method"] == "POST"
    assert "/invite" in op["url"]
    assert op["body"]["recipients"][0]["email"] == "ivanov@tmki.ru"


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
