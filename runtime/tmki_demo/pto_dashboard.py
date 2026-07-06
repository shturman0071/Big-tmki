"""Данные дашборда инженера ПТО (MVP, mock + каталог нормативки)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LEGAL_CATALOG = ROOT / "schemas" / "document" / "legal-corpus-catalog.json"
SEED_PATH = Path(__file__).resolve().parents[1] / "artifacts" / "demo" / "pto-dashboard-seed.json"


def _load_seed() -> dict[str, Any]:
    if SEED_PATH.is_file():
        try:
            return json.loads(SEED_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _regulations_preview(limit: int = 6) -> list[dict[str, Any]]:
    if not LEGAL_CATALOG.is_file():
        return []
    try:
        catalog = json.loads(LEGAL_CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    out: list[dict[str, Any]] = []
    for cat in catalog.get("categories", []):
        for doc in cat.get("documents", []):
            out.append(
                {
                    "doc_key": doc.get("doc_key"),
                    "title": doc.get("title"),
                    "category": cat.get("title"),
                    "status": "monitor",
                    "updated": "еженедельно",
                }
            )
            if len(out) >= limit:
                return out
    return out


def _default_calendar() -> dict[str, Any]:
    now = datetime.now(timezone.utc).astimezone()
    base = now.replace(hour=0, minute=0, second=0, microsecond=0)
    events = [
        {
            "id": "ev1",
            "title": "Планерка ПТО + участки",
            "start": (base + timedelta(days=1, hours=10)).isoformat(),
            "kind": "meeting",
        },
        {
            "id": "ev2",
            "title": "Сдача исполнительной съёмки",
            "start": (base + timedelta(days=2, hours=15)).isoformat(),
            "kind": "deadline",
        },
        {
            "id": "ev3",
            "title": "Согласование КМД — блок 4",
            "start": (base + timedelta(days=4, hours=11)).isoformat(),
            "kind": "task",
        },
    ]
    return {
        "month_label": now.strftime("%B %Y").capitalize(),
        "today": now.strftime("%Y-%m-%d"),
        "events": events,
    }


def build_pto_dashboard(*, index_stats: dict[str, int] | None = None) -> dict[str, Any]:
    seed = _load_seed()
    skru2 = (index_stats or {}).get("skru-2", 0)
    index_pct = round(100.0 * skru2 / 100_804, 1) if skru2 else None

    kanban = seed.get("kanban") or {
        "mode": "deadlines",
        "columns": [
            {
                "id": "overdue",
                "title": "Просрочены",
                "color": "#f06a6a",
                "items": [
                    {
                        "id": "k1",
                        "title": "Ответ на замечания Ростехнадзора по ИД",
                        "deadline_label": "− 19 часов",
                        "deadline_tone": "overdue",
                        "tags": ["#Высокий"],
                        "assignees": ["ИА"],
                        "comments": 2,
                    },
                ],
            },
            {
                "id": "today",
                "title": "На сегодня",
                "color": "#9dcf00",
                "items": [
                    {
                        "id": "k2",
                        "title": "Сверить ведомость объёмов — шахта 3",
                        "deadline_label": "Сегодня, 19:00",
                        "deadline_tone": "today",
                        "tags": ["#ПТО"],
                        "assignees": ["ИА", "СК"],
                        "subtasks": 3,
                    },
                    {
                        "id": "k3",
                        "title": "Согласование графика ПТО на июль",
                        "deadline_label": "Сегодня, 12:00",
                        "deadline_tone": "today",
                        "tags": ["#График"],
                        "assignees": ["ИА"],
                    },
                ],
            },
            {
                "id": "this_week",
                "title": "На этой неделе",
                "color": "#2fc6f6",
                "items": [
                    {
                        "id": "k4",
                        "title": "Комплект ИД — блок 4",
                        "deadline_label": "Пт, 18:00",
                        "deadline_tone": "week",
                        "tags": ["#ИД"],
                        "assignees": ["ИА"],
                        "subtasks": 5,
                    },
                ],
            },
            {
                "id": "next_week",
                "title": "На следующей неделе",
                "color": "#55d0e0",
                "items": [
                    {
                        "id": "k5",
                        "title": "Журнал производства работ — июль",
                        "deadline_label": "12 июл",
                        "deadline_tone": "neutral",
                        "tags": ["#Журнал"],
                        "assignees": ["ИА"],
                    },
                ],
            },
            {
                "id": "no_deadline",
                "title": "Без срока",
                "color": "#a8adb4",
                "items": [
                    {
                        "id": "k6",
                        "title": "Актуализация реестра нормативных ссылок",
                        "deadline_label": "",
                        "deadline_tone": "neutral",
                        "tags": ["#Нормативка"],
                        "assignees": ["ИА"],
                    },
                    {
                        "id": "k7",
                        "title": "Поручение с планерки: акт скрытых работ",
                        "deadline_label": "",
                        "deadline_tone": "neutral",
                        "tags": ["#Планерка"],
                        "assignees": ["СК"],
                    },
                ],
            },
        ],
    }

    return {
        "schema_version": "0.1",
        "role_key": "engineer_pto",
        "role_label": "Инженер ПТО",
        "project": seed.get("project") or "Сатимол",
        "department": seed.get("department") or "ПТО",
        "user": seed.get("user")
        or {
            "display_name": "Инженер ПТО (демо)",
            "employee_id": "emp_pto_demo",
            "department_id": "dept_pto",
        },
        "greeting": seed.get("greeting") or "Рабочее место производственно-технического отдела",
        "modules": [
            {"id": "tasks", "label": "Задачи", "enabled": True},
            {"id": "documents", "label": "Документы", "enabled": True},
            {"id": "calendar", "label": "Календарь", "enabled": True},
            {"id": "regulations", "label": "Нормативная база", "enabled": True},
            {"id": "kanban", "label": "Канбан", "enabled": True},
            {"id": "agent", "label": "ИИ-агент", "enabled": True},
        ],
        "tasks": seed.get("tasks")
        or [
            {
                "id": "task1",
                "title": "Сверить КМД с графиком производства",
                "due": "2026-07-08",
                "status": "in_progress",
            },
            {
                "id": "task2",
                "title": "Подготовить ответ на замечания Ростехнадзора",
                "due": "2026-07-10",
                "status": "open",
            },
            {
                "id": "task3",
                "title": "Актуализировать реестр исполнительной документации",
                "due": "2026-07-12",
                "status": "open",
            },
        ],
        "recent_documents": seed.get("recent_documents")
        or [
            {
                "doc_id": "doc_452",
                "title": "Документ о качестве №452",
                "path": "СКРУ-2/…/Документ о качестве №452.pdf",
                "opened_at": "2026-07-05T11:20:00+03:00",
            },
            {
                "doc_id": "doc_274",
                "title": "Письмо № 274 от 14.06.2022",
                "path": "test_docs/Письмо № 274 от 14.06.2022.pdf",
                "opened_at": "2026-07-05T10:05:00+03:00",
            },
            {
                "doc_id": "doc_kmd",
                "title": "Замечания КМД — армировка",
                "path": "test_docs/Замечания КМД.pdf",
                "opened_at": "2026-07-04T16:30:00+03:00",
            },
        ],
        "calendar": seed.get("calendar") or _default_calendar(),
        "regulations": seed.get("regulations") or _regulations_preview(6),
        "kanban": kanban,
        "apps": seed.get("apps")
        or {
            "mail": {
                "label": "Почта",
                "url": "https://outlook.office.com/mail/",
                "external": True,
            },
            "disk": {
                "label": "Мой диск",
                "url": "https://www.office.com/launch/onedrive",
                "external": True,
            },
            "apps_hub": {
                "label": "Приложения",
                "url": "https://www.office.com/apps",
                "external": True,
            },
            "max": {
                "label": "Макс",
                "url": "https://web.max.ru",
                "external": True,
            },
            "settings": {
                "label": "Настройки",
                "url": "#settings",
                "external": False,
            },
        },
        "attention": seed.get("attention")
        or [
            {
                "level": "critical",
                "text": "Просрочка сдачи ИД по шахте 3 — 5 дней",
            },
            {
                "level": "warning",
                "text": "3 документа без классификации в реестре ПТО",
            },
            {
                "level": "warning",
                "text": "Замечания КМД — ожидают ответа инженера",
            },
        ],
        "todo_groups": seed.get("todo_groups")
        or [
            {
                "id": "satimol",
                "title": "Дела · Сатимол",
                "items": [
                    "Сверить ведомость объёмов с графиком",
                    "Запросить акт скрытых работ",
                ],
            },
            {
                "id": "id_kit",
                "title": "Дела · Исполнительная документация",
                "items": [
                    "Комплект ИД — блок 4",
                    "Журнал производства работ — июль",
                ],
            },
        ],
        "agent": {
            "label": "ИИ-агент ТМКИ",
            "hint": "Поиск по регламентам и нормативке с цитатами",
            "corpus_default": "skru-2",
            "chat_url": "/",
        },
        "system": {
            "index_skru2_chunks": skru2,
            "index_skru2_percent": index_pct,
            "demo_mode": "pto_dashboard_v0",
        },
    }
