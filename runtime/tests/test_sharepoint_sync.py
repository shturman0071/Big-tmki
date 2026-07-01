from pathlib import Path

from tmki_rag import load_folder_catalog, load_folder_grants
from tmki_sharepoint import StubSharePointAdapter, build_sync_plan

ROOT = Path(__file__).resolve().parents[2]


def test_build_sync_plan_from_grants():
    folders = load_folder_catalog(ROOT / "schemas/document/examples/satimol-folders.example.json")
    grants = load_folder_grants(ROOT / "schemas/org/examples/satimol-folder-grants.example.json")
    plan = build_sync_plan(grants, folders)
    assert len(plan) >= 2
    assert any(c.action == "remove_read" for c in plan)
    assert any(c.action == "add_read" for c in plan)


def test_stub_adapter_apply():
    folders = load_folder_catalog(ROOT / "schemas/document/examples/satimol-folders.example.json")
    grants = load_folder_grants(ROOT / "schemas/org/examples/satimol-folder-grants.example.json")
    adapter = StubSharePointAdapter()
    result = adapter.apply(build_sync_plan(grants, folders))
    assert result["adapter"] == "stub"
    assert result["changes_applied"] == len(adapter.applied)
