"""Данные управленческого дашборда (Direktor / руководитель)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SEED_PATH = Path(__file__).resolve().parents[1] / "artifacts" / "demo" / "director-dashboard-seed.json"


def _load_seed() -> dict[str, Any]:
    if SEED_PATH.is_file():
        try:
            return json.loads(SEED_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _builtin_seed() -> dict[str, Any]:
    return {
        "project": "Сатимол",
        "user": {
            "display_name": "Каледин О.С.",
            "employee_id": "emp_direktor_001",
            "department_id": "dept_leadership",
        },
        "objects": [
            {
                "id": "all",
                "name": "Все объекты",
                "region": "Глобально",
                "type": "единая связанная сеть",
                "status": "активно",
            },
            {
                "id": "satimola",
                "name": "Сатимола",
                "region": "Казахстан",
                "type": "строительство новых стволов",
                "status": "активно",
            },
            {
                "id": "berezniki",
                "name": "Березники",
                "region": "Россия, Пермский край",
                "type": "база оборудования",
                "status": "активно",
            },
            {
                "id": "germany",
                "name": "Германия",
                "region": "Евросоюз",
                "type": "поставщики и документы",
                "status": "контроль",
            },
        ],
        "briefs": {
            "all": (
                "Общая картина: договоры на согласовании, дебиторка, платежи, расходы "
                "и новости по трудовому/санкционному/налоговому контуру требуют внимания."
            ),
            "satimola": (
                "Сатимола: фокус на строительстве, платежах, поставках оборудования "
                "и сроках согласования."
            ),
            "berezniki": (
                "Березники: фокус на подготовке оборудования, ремонте, документах "
                "и отправке на связанные объекты."
            ),
            "germany": (
                "Германия: фокус на международных документах, поставщиках, переводах "
                "и санкционном мониторинге."
            ),
        },
        "contracts": [
            {
                "name": "СМР-САТ-024",
                "object": "Сатимола",
                "scope": "satimola",
                "status": "На согласовании",
                "category": "approval",
                "end": "2026-08-20",
                "amount": 860,
                "actual": 180,
                "expected": 240,
                "risk": "Критичный",
                "owner": "Юридический блок",
                "counterparty": "Satimola Mining LLP",
            },
            {
                "name": "АРЕНДА-БЕР-011",
                "object": "Березники",
                "scope": "berezniki",
                "status": "Действует",
                "category": "expiring",
                "end": "2026-06-18",
                "amount": 180,
                "actual": 90,
                "expected": 40,
                "risk": "Высокий",
                "owner": "База",
                "counterparty": "ТехАренда Плюс",
            },
            {
                "name": "ПОСТАВКА-САТ-009",
                "object": "Сатимола",
                "scope": "satimola",
                "status": "Действует",
                "category": "active",
                "end": "2026-12-31",
                "amount": 540,
                "actual": 220,
                "expected": 180,
                "risk": "Высокий",
                "owner": "Снабжение",
                "counterparty": "Kaz Supply Group",
            },
            {
                "name": "СЕРВИС-БЕР-004",
                "object": "Березники",
                "scope": "berezniki",
                "status": "Действует",
                "category": "active",
                "end": "2026-10-10",
                "amount": 70,
                "actual": 20,
                "expected": 20,
                "risk": "Средний",
                "owner": "Механик",
                "counterparty": "РемСервис",
            },
            {
                "name": "ПРОЕКТ-САТ-015",
                "object": "Сатимола",
                "scope": "satimola",
                "status": "Действует",
                "category": "active",
                "end": "2027-03-15",
                "amount": 940,
                "actual": 310,
                "expected": 260,
                "risk": "Средний",
                "owner": "ПТО",
                "counterparty": "ПроектШахт",
            },
            {
                "name": "ПОСТАВЩИК-DE-003",
                "object": "Германия",
                "scope": "germany",
                "status": "На согласовании",
                "category": "approval",
                "end": "2026-09-30",
                "amount": 420,
                "actual": 0,
                "expected": 110,
                "risk": "Высокий",
                "owner": "Снабжение",
                "counterparty": "Ruhr Technik GmbH",
            },
            {
                "name": "ДОК-DE-007",
                "object": "Германия",
                "scope": "germany",
                "status": "Действует",
                "category": "expiring",
                "end": "2026-06-12",
                "amount": 150,
                "actual": 60,
                "expected": 30,
                "risk": "Средний",
                "owner": "Документооборот",
                "counterparty": "Nord Consult GmbH",
            },
        ],
        "finance_series": [
            {"ym": "2025-11", "actual": 180, "expected": 95, "expenses": 130},
            {"ym": "2025-12", "actual": 210, "expected": 120, "expenses": 150},
            {"ym": "2026-01", "actual": 260, "expected": 160, "expenses": 190},
            {"ym": "2026-02", "actual": 220, "expected": 210, "expenses": 205},
            {"ym": "2026-03", "actual": 310, "expected": 180, "expenses": 240},
            {"ym": "2026-04", "actual": 290, "expected": 250, "expenses": 260},
            {"ym": "2026-05", "actual": 350, "expected": 220, "expenses": 300},
            {"ym": "2026-06", "actual": 420, "expected": 290, "expenses": 365},
            {"ym": "2026-07", "actual": 260, "expected": 410, "expenses": 330},
            {"ym": "2026-08", "actual": 300, "expected": 360, "expenses": 315},
            {"ym": "2026-09", "actual": 380, "expected": 340, "expenses": 355},
            {"ym": "2026-10", "actual": 460, "expected": 380, "expenses": 390},
        ],
        "expenses": [
            {"ym": "2026-05", "amount": 300, "marker": "закупки"},
            {"ym": "2026-06", "amount": 365, "marker": "логистика"},
            {"ym": "2026-07", "amount": 330, "marker": "ремонт"},
            {"ym": "2026-08", "amount": 315, "marker": "командировки"},
        ],
        "expense_details": [
            {
                "category": "Оборудование",
                "account": "60.01",
                "invoice": "Счет 45-БЕР",
                "contract": "АРЕНДА-БЕР-011",
                "amount": 96,
                "ks2": "нет",
                "ks3": "нет",
                "status": "к оплате",
            },
            {
                "category": "СМР",
                "account": "20.01",
                "invoice": "Счет 118-САТ",
                "contract": "СМР-САТ-024",
                "amount": 142,
                "ks2": "КС-2 N14",
                "ks3": "КС-3 N14",
                "status": "акт на проверке",
            },
            {
                "category": "Логистика",
                "account": "44.02",
                "invoice": "Счет 77-Л",
                "contract": "ПОСТАВКА-САТ-009",
                "amount": 58,
                "ks2": "нет",
                "ks3": "нет",
                "status": "ожидает первичку",
            },
            {
                "category": "Ремонт",
                "account": "25.03",
                "invoice": "Счет 31-Р",
                "contract": "СЕРВИС-БЕР-004",
                "amount": 39,
                "ks2": "КС-2 N3",
                "ks3": "КС-3 N3",
                "status": "закрыт",
            },
            {
                "category": "Командировки",
                "account": "26.05",
                "invoice": "Авансовый отчет 19",
                "contract": "ПРОЕКТ-САТ-015",
                "amount": 30,
                "ks2": "нет",
                "ks3": "нет",
                "status": "проверка",
            },
        ],
        "debtors": [
            {
                "counterparty": "Satimola Mining LLP",
                "contract": "СМР-САТ-024",
                "scope": "satimola",
                "overdue": 74,
                "days": 19,
            },
            {
                "counterparty": "ТехАренда Плюс",
                "contract": "АРЕНДА-БЕР-011",
                "scope": "berezniki",
                "overdue": 32,
                "days": 14,
            },
            {
                "counterparty": "Kaz Supply Group",
                "contract": "ПОСТАВКА-САТ-009",
                "scope": "satimola",
                "overdue": 48,
                "days": 8,
            },
            {
                "counterparty": "Nord Consult GmbH",
                "contract": "ДОК-DE-007",
                "scope": "germany",
                "overdue": 18,
                "days": 11,
            },
        ],
        "litigation": [
            {
                "counterparty": "Контрагент Строй-Сервис",
                "reason": "спор по оплате актов",
                "amount": 22,
            },
            {
                "counterparty": "Logistics KZ Partner",
                "reason": "претензия по срокам поставки",
                "amount": 11,
            },
            {
                "counterparty": "Old Equipment Trade",
                "reason": "возврат аванса",
                "amount": 8,
            },
        ],
        "overdue_items": [
            {
                "title": "Просрочено согласование приложения к СМР-САТ-024",
                "object": "Сатимола",
                "scope": "satimola",
                "type": "Договор",
                "days": 9,
                "owner": "Юридический блок",
            },
            {
                "title": "Не получен ожидаемый платеж по АРЕНДА-БЕР-011",
                "object": "Березники",
                "scope": "berezniki",
                "type": "Платеж",
                "days": 14,
                "owner": "Финансы",
            },
            {
                "title": "Не закрыты замечания по поставке оборудования",
                "object": "Сатимола",
                "scope": "satimola",
                "type": "Задача",
                "days": 6,
                "owner": "ПТО",
            },
            {
                "title": "Не хватает подписанного пакета документов поставщика",
                "object": "Германия",
                "scope": "germany",
                "type": "Документ",
                "days": 4,
                "owner": "Снабжение",
            },
            {
                "title": "Фотофиксация насосной станции не обновлена",
                "object": "Березники",
                "scope": "berezniki",
                "type": "Документ",
                "days": 3,
                "owner": "База",
            },
        ],
        "risks": [
            {
                "title": "Задержка отправки проходческого комплекса",
                "object": "Березники -> Сатимола",
                "scope": "berezniki",
                "level": "Критичный",
                "category": "Техника",
                "owner": "Механик",
            },
            {
                "title": "Договор СМР-САТ-024 не согласован",
                "object": "Сатимола",
                "scope": "satimola",
                "level": "Критичный",
                "category": "Договор",
                "owner": "Юристы",
            },
            {
                "title": "Ожидаемый платеж может сдвинуть график закупок",
                "object": "Сатимола",
                "scope": "satimola",
                "level": "Высокий",
                "category": "Деньги",
                "owner": "Финансы",
            },
            {
                "title": "Неполный комплект немецких документов",
                "object": "Германия",
                "scope": "germany",
                "level": "Высокий",
                "category": "Документы",
                "owner": "Снабжение",
            },
            {
                "title": "Насосная станция в ремонте без даты готовности",
                "object": "Березники",
                "scope": "berezniki",
                "level": "Средний",
                "category": "Оборудование",
                "owner": "База",
            },
        ],
        "news": [
            {
                "id": "ru-labor",
                "country": "Россия",
                "title": "Мониторинг изменений трудового законодательства для вахтового персонала",
                "tag": "Трудовое право",
                "source": "Официальное опубликование правовых актов",
                "url": "http://publication.pravo.gov.ru/",
            },
            {
                "id": "eu-sanctions",
                "country": "Евросоюз",
                "title": "Проверка санкционных ограничений по поставщикам и оборудованию",
                "tag": "Санкции",
                "source": "EUR-Lex",
                "url": "https://eur-lex.europa.eu/",
            },
            {
                "id": "kz-tax",
                "country": "Казахстан",
                "title": "Контроль налоговых и разрешительных изменений для строительных контрактов",
                "tag": "Налоги и финансы",
                "source": "Адилет",
                "url": "https://adilet.zan.kz/",
            },
        ],
        "todo_groups": [
            {
                "id": "berezniki-main",
                "title": "Дела · Березники",
                "scope": "berezniki",
                "items": [
                    {
                        "title": "Подтвердить готовность проходческого комплекса",
                        "status": "В работе",
                        "priority": "high",
                        "owner": "База",
                    },
                    {
                        "title": "Собрать фотофиксацию оборудования",
                        "status": "Новая",
                        "priority": "medium",
                        "owner": "База",
                    },
                    {
                        "title": "Проверить документы на отгрузку",
                        "status": "Просрочена",
                        "priority": "high",
                        "owner": "Документооборот",
                    },
                ],
            },
            {
                "id": "satimola-main",
                "title": "Дела · Сатимола",
                "scope": "satimola",
                "items": [
                    {
                        "title": "Согласовать договор СМР-САТ-024",
                        "status": "На согласовании",
                        "priority": "high",
                        "owner": "Юристы",
                    },
                    {
                        "title": "Обновить график поставки",
                        "status": "В работе",
                        "priority": "medium",
                        "owner": "ПТО",
                    },
                    {
                        "title": "Проверить платежный календарь",
                        "status": "Ожидает",
                        "priority": "medium",
                        "owner": "Финансы",
                    },
                ],
            },
            {
                "id": "germany-main",
                "title": "Дела · Германия",
                "scope": "germany",
                "items": [
                    {
                        "title": "Запросить документы поставщика",
                        "status": "В работе",
                        "priority": "high",
                        "owner": "Снабжение",
                    },
                    {
                        "title": "Проверить перевод договора",
                        "status": "Новая",
                        "priority": "medium",
                        "owner": "Юристы",
                    },
                    {
                        "title": "Уточнить сроки ответа",
                        "status": "Ожидает",
                        "priority": "medium",
                        "owner": "Снабжение",
                    },
                ],
            },
        ],
        "todo_files": {
            "berezniki-main": [
                {
                    "date": "2026-05-22",
                    "file": "todo-berezniki-2026-05-22.docx",
                    "text": "Готовность оборудования, фотофиксация, документы на отгрузку",
                },
                {
                    "date": "2026-05-15",
                    "file": "todo-berezniki-2026-05-15.docx",
                    "text": "Насосная станция, ремонт, склад",
                },
            ],
            "satimola-main": [
                {
                    "date": "2026-05-22",
                    "file": "todo-satimola-2026-05-22.docx",
                    "text": "СМР-САТ-024, график поставки, платежный календарь",
                },
                {
                    "date": "2026-05-10",
                    "file": "todo-satimola-2026-05-10.docx",
                    "text": "ПТО, договоры, сроки",
                },
            ],
            "germany-main": [
                {
                    "date": "2026-05-22",
                    "file": "todo-germany-2026-05-22.docx",
                    "text": "документы поставщика, перевод договора, сроки ответа",
                }
            ],
        },
    }


def ensure_seed_file() -> None:
    if SEED_PATH.is_file():
        return
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEED_PATH.write_text(
        json.dumps(_builtin_seed(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def build_director_dashboard(*, index_stats: dict[str, int] | None = None) -> dict[str, Any]:
    ensure_seed_file()
    seed = _load_seed()
    data = _deep_merge(_builtin_seed(), seed)
    skru2 = (index_stats or {}).get("skru-2", 0)
    index_pct = round(100.0 * skru2 / 100_804, 1) if skru2 else None

    return {
        "schema_version": "0.1",
        "role_key": "Direktor",
        "role_label": "Директор",
        "project": data.get("project") or "Сатимол",
        "user": data.get("user")
        or {
            "display_name": "Директор (демо)",
            "employee_id": "emp_direktor_demo",
            "department_id": "dept_leadership",
        },
        "greeting": "Управленческий дашборд TMKI Control Center",
        "objects": data.get("objects") or [],
        "briefs": data.get("briefs") or {},
        "contracts": data.get("contracts") or [],
        "finance_series": data.get("finance_series") or [],
        "expenses": data.get("expenses") or [],
        "expense_details": data.get("expense_details") or [],
        "debtors": data.get("debtors") or [],
        "litigation": data.get("litigation") or [],
        "overdue_items": data.get("overdue_items") or [],
        "risks": data.get("risks") or [],
        "news": data.get("news") or [],
        "todo_groups": data.get("todo_groups") or [],
        "todo_files": data.get("todo_files") or {},
        "agent": {
            "label": "ИИ-агент ТМКИ",
            "hint": "Управленческая сводка по договорам, финансам и рискам",
            "corpus_default": "skru-2",
            "chat_url": "/",
        },
        "system": {
            "index_skru2_chunks": skru2,
            "index_skru2_percent": index_pct,
            "demo_mode": "director_dashboard_v0",
            "source": "ТМКИ проект 1 / prototype",
        },
    }
