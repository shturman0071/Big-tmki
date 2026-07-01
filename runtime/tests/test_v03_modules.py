from pathlib import Path

import pytest

from tmki_desktop_sync.provision import provision_employee_desktop
from tmki_hr import HrCardAccessError, HrCardStore
from tmki_voice import extract_todo_items, get_stt_provider


def test_provision_employee_desktop(tmp_path):
    desk_root = tmp_path / "Desktop"
    result = provision_employee_desktop(
        employee_id="emp_x",
        display_name="Иванов И.",
        desktop_root=desk_root,
        server_base=tmp_path / "server",
        manifest_dir=tmp_path / "manifests",
    )
    assert result.created_desktop is True
    assert Path(result.desktop_path).is_dir()
    assert Path(result.manifest_path).is_file()


def test_hr_card_requires_consent(tmp_path):
    store = HrCardStore(tmp_path)
    with pytest.raises(ValueError, match="consent_signed"):
        store.save(
            {"schema_version": "0.1", "employee_id": "emp_x", "consent_signed": False, "hr_fields": {}},
            actor_role="Кадры",
        )


def test_hr_card_access_denied(tmp_path):
    store = HrCardStore(tmp_path)
    with pytest.raises(HrCardAccessError):
        store.load("emp_x", actor_role="Сотрудник подразделения")


def test_hr_card_save_and_load(tmp_path):
    store = HrCardStore(tmp_path)
    card = {
        "schema_version": "0.1",
        "employee_id": "emp_x",
        "consent_signed": True,
        "hr_fields": {"position": "инженер"},
        "voice_profile": {"enrolled": True, "profile_ref": "vault://voice/emp_x"},
    }
    store.save(card, actor_role="Кадры")
    loaded = store.load("emp_x", actor_role="Кадры")
    assert loaded["voice_profile"]["enrolled"] is True


def test_extract_todo_items():
    text = "Обсудили кран.\nНужно: подготовить акт осмотра\nОбычная реплика"
    items = extract_todo_items(text)
    assert len(items) == 1
    assert "акт осмотра" in items[0].text


def test_stt_stub_provider():
    result = get_stt_provider().transcribe("dummy.wav")
    assert result.provider == "stub"
