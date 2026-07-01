from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HR_ALLOWED_ROLES = frozenset({"Кадры", "Владелец ИБ", "security", "hr"})
DEFAULT_STORE = Path(__file__).resolve().parents[1] / "artifacts" / "hr-cards"


class HrCardAccessError(PermissionError):
    pass


class HrCardStore:
    """Изолированное хранилище HR-карточек (#48). Не индексируется в RAG."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or DEFAULT_STORE
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, employee_id: str) -> Path:
        safe = employee_id.replace("/", "_")
        return self.root / f"{safe}.hr.json"

    def load(self, employee_id: str, *, actor_role: str) -> dict[str, Any]:
        if actor_role not in HR_ALLOWED_ROLES:
            raise HrCardAccessError(f"Доступ к HR-карточке запрещён для роли: {actor_role}")
        path = self._path(employee_id)
        if not path.is_file():
            raise FileNotFoundError(f"HR card не найдена: {employee_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, card: dict[str, Any], *, actor_role: str) -> Path:
        if actor_role not in HR_ALLOWED_ROLES:
            raise HrCardAccessError(f"Запись HR-карточки запрещена для роли: {actor_role}")
        if not card.get("consent_signed"):
            raise ValueError("consent_signed MUST be true для сохранения voice/anthropometrics")
        employee_id = card["employee_id"]
        card = {**card, "access_restricted": True}
        path = self._path(employee_id)
        path.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
        return path


def load_hr_card(employee_id: str, *, actor_role: str, store: HrCardStore | None = None) -> dict[str, Any]:
    return (store or HrCardStore()).load(employee_id, actor_role=actor_role)


def save_hr_card(card: dict[str, Any], *, actor_role: str, store: HrCardStore | None = None) -> Path:
    return (store or HrCardStore()).save(card, actor_role=actor_role)
