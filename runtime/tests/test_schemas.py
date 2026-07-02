"""Проверка JSON-артефактов schemas/ (парсинг и наличие ключевых контрактов)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"

REQUIRED_FILES = [
    "tools/tool-definition.schema.json",
    "tools/tool-call-request.schema.json",
    "tools/tool-call-response.schema.json",
    "runtime/mvp-flow.json",
    "runtime/run.schema.json",
    "runtime/step.schema.json",
    "runtime/event.schema.json",
    "runtime/loop-state.schema.json",
    "runtime/common.schema.json",
    "runtime/audit-event-catalog.json",
    "org/examples/satimol-snapshot.example.json",
    "runtime/examples/policy-context-contractor.example.json",
    "voice/voice-session.schema.json",
    "security/mvp-security-review.checklist.json",
]


@pytest.mark.parametrize("rel_path", REQUIRED_FILES)
def test_required_schema_files_exist(rel_path: str) -> None:
    path = SCHEMAS / rel_path
    assert path.is_file(), f"Отсутствует обязательный файл: {rel_path}"


def test_all_schema_json_files_parse() -> None:
    errors: list[str] = []
    for path in sorted(SCHEMAS.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    assert not errors, "JSON parse errors:\n" + "\n".join(errors)


def test_satimol_snapshot_has_contractor() -> None:
    data = json.loads((SCHEMAS / "org/examples/satimol-snapshot.example.json").read_text(encoding="utf-8"))
    employees = {e["employee_id"]: e for e in data.get("employees", [])}
    assert "emp_contractor_01" in employees
    assert employees["emp_contractor_01"].get("contractor_id") == "contractor_ks_sub"
    roles = {a["employee_id"]: a.get("project_role") for a in data.get("assignments", [])}
    assert roles.get("emp_contractor_01") == "Подрядчик (external)"


def test_mvp_flow_has_stages() -> None:
    flow = json.loads((SCHEMAS / "runtime/mvp-flow.json").read_text(encoding="utf-8"))
    stages = flow.get("stages") or flow.get("steps") or []
    assert len(stages) >= 4


def test_tool_gating_uses_gates_key() -> None:
    rules = json.loads((SCHEMAS / "tools/tool-gating.rules.json").read_text(encoding="utf-8"))
    assert isinstance(rules.get("gates"), list)
    assert rules["gates"], "gates не должен быть пустым"
