from pathlib import Path

from tmki_desktop_sync import DesktopSyncWatcher, desktop_folder_for_employee, default_server_path
from tmki_ingest.document_policy import resolve_external_law_check, validate_document_creation_policy


def test_desktop_folder_for_employee():
    path = desktop_folder_for_employee("Литовский Д.", desktop_root=Path("/Desktop"))
    assert path == Path("/Desktop/Литовский")


def test_desktop_sync_copies_new_file(tmp_path):
    desk = tmp_path / "desktop" / "Иванов"
    server = tmp_path / "server"
    desk.mkdir(parents=True)
    (desk / "doc.txt").write_text("рабочий файл", encoding="utf-8")

    watcher = DesktopSyncWatcher(
        desktop_path=desk,
        server_path=server,
        employee_id="emp_test",
        interval_sec=1,
    )
    records = watcher.sync_once()
    assert any(r.action == "copied" for r in records)
    assert (server / "doc.txt").read_text(encoding="utf-8") == "рабочий файл"

    records2 = watcher.sync_once()
    assert all(r.action == "skipped" for r in records2)


def test_document_policy_contract_always():
    assert resolve_external_law_check("contract") == "always"


def test_document_policy_other_default_never():
    assert resolve_external_law_check("report") == "never"
    assert resolve_external_law_check("report", user_requested_law_check=True) == "on_user_request"


def test_validate_document_creation_policy():
    out = validate_document_creation_policy(
        {"schema_version": "0.1", "document_type": "instruction", "use_internal_templates": True}
    )
    assert out["external_law_check"] == "never"
