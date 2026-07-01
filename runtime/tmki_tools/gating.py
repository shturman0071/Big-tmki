from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# project_role → role_group (дополнение к tool-gating.rules.json)
_ROLE_GROUP_ALIASES: dict[str, str] = {
    "Chefmarkscheider": "site_ops",
    "Сотрудник подразделения": "site_ops",
    "Подрядчик (external)": "contractor",
    "Hauptingenieur": "engineering_leads",
    "Главный инженер проекта": "engineering_leads",
    "Начальник подразделения": "engineering_leads",
    "МТО": "support_mto",
    "Закупки": "support_mto",
    "Бухгалтерия": "finance_hr",
    "Кадры": "finance_hr",
    "ИТ": "it",
    "Связь": "it",
}


@dataclass(frozen=True)
class GatingDecision:
    allowed: bool
    deny_reason: str | None = None
    gate: dict[str, Any] | None = None


def load_gating_rules(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _role_groups_for(project_role: str, rules: dict[str, Any]) -> set[str]:
    groups: set[str] = set()
    alias = _ROLE_GROUP_ALIASES.get(project_role)
    if alias:
        groups.add(alias)
    for group_name, roles in rules.get("role_groups", {}).items():
        if project_role in roles:
            groups.add(group_name)
    return groups


def _find_gate(tool_id: str, rules: dict[str, Any]) -> dict[str, Any] | None:
    for gate in rules.get("gates", []):
        if gate.get("tool_id") == tool_id:
            return gate
    return None


def check_policy(
    tool_id: str,
    policy_context: dict[str, Any],
    rules: dict[str, Any],
) -> GatingDecision:
    gate = _find_gate(tool_id, rules)
    if not gate:
        return GatingDecision(allowed=False, deny_reason="tool_disabled")

    env = policy_context.get("env", "production")
    if env not in gate.get("env_allowlist", []):
        return GatingDecision(allowed=False, deny_reason="env_not_allowed")

    role = policy_context.get("project_role", "")
    groups = _role_groups_for(role, rules)

    deny_groups = set(gate.get("deny_role_groups", []))
    if groups & deny_groups:
        return GatingDecision(allowed=False, deny_reason="insufficient_role")

    allow_groups = set(gate.get("allow_role_groups", []))
    if allow_groups and not (groups & allow_groups):
        return GatingDecision(allowed=False, deny_reason="insufficient_role")

    return GatingDecision(allowed=True, gate=gate)
