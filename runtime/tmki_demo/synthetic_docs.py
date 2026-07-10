"""Синтетическое дерево документов для управленческого дашборда.

Виртуальный каталог: договоры и To-do. В конечных папках — до 5 файлов.
Поиск и открытие через API / клик в UI (os.startfile).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parents[1]
ROOT = RUNTIME / "artifacts" / "demo" / "synthetic-docs"

_CONTRACT_SPECS: list[dict[str, str]] = [
    {
        "name": "СМР-САТ-024",
        "object": "Сатимола",
        "folder": "Договоры/Сатимола",
        "counterparty": "Satimola Mining LLP",
        "body": (
            "ДОГОВОР ПОДРЯДА № СМР-САТ-024\n"
            "Заказчик: ООО «ТМКИ»\n"
            "Подрядчик: Satimola Mining LLP\n"
            "Объект: Сатимола\n"
            "Предмет: строительно-монтажные работы.\n"
            "Срок окончания: 20.08.2026\n"
            "Сумма: 860 млн ₽\n"
            "Статус: на согласовании.\n"
            "Риск: критичный — отставание по графику платежей.\n"
        ),
    },
    {
        "name": "ПОСТАВКА-САТ-009",
        "object": "Сатимола",
        "folder": "Договоры/Сатимола",
        "counterparty": "Kaz Supply Group",
        "body": (
            "ДОГОВОР ПОСТАВКИ № ПОСТАВКА-САТ-009\n"
            "Поставщик: Kaz Supply Group\n"
            "Объект: Сатимола\n"
            "Срок: до 31.12.2026\n"
            "Сумма: 540 млн ₽\n"
            "Статус: действует.\n"
        ),
    },
    {
        "name": "ПРОЕКТ-САТ-015",
        "object": "Сатимола",
        "folder": "Договоры/Сатимола",
        "counterparty": "ПроектШахт",
        "body": (
            "ДОГОВОР НА ПРОЕКТНЫЕ РАБОТЫ № ПРОЕКТ-САТ-015\n"
            "Исполнитель: ПроектШахт\n"
            "Объект: Сатимола\n"
            "Срок: до 15.03.2027\n"
            "Сумма: 940 млн ₽\n"
        ),
    },
    {
        "name": "АРЕНДА-БЕР-011",
        "object": "Березники",
        "folder": "Договоры/Березники",
        "counterparty": "ТехАренда Плюс",
        "body": (
            "ДОГОВОР АРЕНДЫ № АРЕНДА-БЕР-011\n"
            "Арендодатель: ТехАренда Плюс\n"
            "Объект: Березники\n"
            "Окончание: 18.06.2026 (остался 1 месяц)\n"
            "Сумма: 180 млн ₽\n"
        ),
    },
    {
        "name": "СЕРВИС-БЕР-004",
        "object": "Березники",
        "folder": "Договоры/Березники",
        "counterparty": "РемСервис",
        "body": (
            "ДОГОВОР СЕРВИСА № СЕРВИС-БЕР-004\n"
            "Исполнитель: РемСервис\n"
            "Объект: Березники\n"
            "Окончание: 10.10.2026\n"
            "Сумма: 70 млн ₽\n"
        ),
    },
    {
        "name": "ПОСТАВЩИК-DE-003",
        "object": "Германия",
        "folder": "Договоры/Германия",
        "counterparty": "Ruhr Technik GmbH",
        "body": (
            "ДОГОВОР ПОСТАВКИ № ПОСТАВЩИК-DE-003\n"
            "Поставщик: Ruhr Technik GmbH\n"
            "Направление: Германия\n"
            "Статус: на согласовании\n"
            "Сумма: 420 млн ₽\n"
            "Примечание: требуется перевод спецификации.\n"
        ),
    },
    {
        "name": "ДОК-DE-007",
        "object": "Германия",
        "folder": "Договоры/Германия",
        "counterparty": "DocuEuro",
        "body": (
            "ДОГОВОР ДОКУМЕНТООБОРОТА № ДОК-DE-007\n"
            "Исполнитель: DocuEuro\n"
            "Окончание: 12.06.2026\n"
            "Сумма: 150 млн ₽\n"
            "Статус: действует, истекает через месяц.\n"
        ),
    },
]

_TODO_SPECS: list[dict[str, Any]] = [
    {
        "group_id": "berezniki-main",
        "folder": "To-do/Березники",
        "files": [
            ("todo-berezniki-2026-05-22.txt", "2026-05-22", "Готовность оборудования, фотофиксация, документы на отгрузку"),
            ("todo-berezniki-2026-05-15.txt", "2026-05-15", "Насосная станция, ремонт, склад"),
            ("todo-berezniki-2026-05-08.txt", "2026-05-08", "Проверка склада и комплектация"),
            ("todo-berezniki-2026-05-01.txt", "2026-05-01", "План мая: отгрузка и ремонт"),
            ("todo-berezniki-checklist.txt", "2026-05-22", "Чек-лист: насос, фото, ТТН, акт"),
        ],
    },
    {
        "group_id": "satimola-main",
        "folder": "To-do/Сатимола",
        "files": [
            ("todo-satimola-2026-05-22.txt", "2026-05-22", "СМР-САТ-024, график поставки, платежный календарь"),
            ("todo-satimola-2026-05-10.txt", "2026-05-10", "ПТО, договоры, сроки"),
            ("todo-satimola-2026-05-03.txt", "2026-05-03", "Согласование графика СМР"),
            ("todo-satimola-risks.txt", "2026-05-22", "Риски: платежи, поставка, ПТО"),
            ("todo-satimola-owners.txt", "2026-05-22", "Ответственные: ПТО, снабжение, юристы"),
        ],
    },
    {
        "group_id": "germany-main",
        "folder": "To-do/Германия",
        "files": [
            ("todo-germany-2026-05-22.txt", "2026-05-22", "документы поставщика, перевод договора, сроки ответа"),
            ("todo-germany-2026-05-18.txt", "2026-05-18", "Санкционный мониторинг поставщиков"),
            ("todo-germany-translation.txt", "2026-05-22", "Перевод договора и приложений"),
            ("todo-germany-shipments.txt", "2026-05-20", "Отгрузки и инвойсы"),
            ("todo-germany-contacts.txt", "2026-05-22", "Контакты EuroFreight и юристов"),
        ],
    },
]

_FILLERS = (
    "реестр-сопроводительных.txt",
    "заметки-совещания.txt",
    "чеклист-проверки.txt",
    "контакты-ответственных.txt",
)


def root_path() -> Path:
    return ROOT


def ensure_synthetic_tree() -> Path:
    """Создать дерево и файлы (идемпотентно)."""
    ROOT.mkdir(parents=True, exist_ok=True)
    for spec in _CONTRACT_SPECS:
        folder = ROOT / spec["folder"]
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{spec['name']}.txt"
        if not path.is_file():
            path.write_text(spec["body"], encoding="utf-8")
        _ensure_leaf_count(folder, prefix=spec["object"])

    for group in _TODO_SPECS:
        folder = ROOT / group["folder"]
        folder.mkdir(parents=True, exist_ok=True)
        for fname, date, text in group["files"]:
            path = folder / fname
            if not path.is_file():
                path.write_text(
                    f"TO-DO · {group['group_id']}\nДата: {date}\n\n{text}\n",
                    encoding="utf-8",
                )
        _ensure_leaf_count(folder, prefix=group["group_id"])

    marker = ROOT / ".ready"
    marker.write_text("ok\n", encoding="utf-8")
    return ROOT


def _ensure_leaf_count(folder: Path, *, prefix: str, target: int = 5) -> None:
    files = [p for p in folder.iterdir() if p.is_file()]
    i = 0
    while len(files) < target and i < len(_FILLERS):
        path = folder / f"{prefix}-{_FILLERS[i]}"
        if not path.is_file():
            path.write_text(
                f"Служебный файл демо-дерева ({prefix}).\nПапка: {folder.name}\n",
                encoding="utf-8",
            )
            files.append(path)
        i += 1


def contract_path(name: str) -> Path | None:
    ensure_synthetic_tree()
    for spec in _CONTRACT_SPECS:
        if spec["name"] == name:
            path = ROOT / spec["folder"] / f"{spec['name']}.txt"
            return path if path.is_file() else None
    # fallback by filename search
    for path in ROOT.rglob(f"{name}.txt"):
        if path.is_file():
            return path
    return None


def todo_file_path(group_id: str, file_name: str) -> Path | None:
    ensure_synthetic_tree()
    for group in _TODO_SPECS:
        if group["group_id"] != group_id:
            continue
        path = ROOT / group["folder"] / file_name
        if path.is_file():
            return path
        # allow .docx names from seed → .txt on disk
        stem = Path(file_name).stem
        for candidate in (ROOT / group["folder"]).glob(f"{stem}.*"):
            if candidate.is_file():
                return candidate
    return None


def enrich_contracts(contracts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ensure_synthetic_tree()
    out: list[dict[str, Any]] = []
    for row in contracts:
        item = dict(row)
        path = contract_path(str(item.get("name") or ""))
        if path:
            item["absolute_path"] = str(path)
            item["relative_path"] = str(path.relative_to(ROOT)).replace("\\", "/")
            item["file_name"] = path.name
        out.append(item)
    return out


def enrich_todo_files(todo_files: dict[str, Any]) -> dict[str, Any]:
    ensure_synthetic_tree()
    out: dict[str, Any] = {}
    for group_id, files in (todo_files or {}).items():
        enriched = []
        for row in files or []:
            item = dict(row)
            fname = str(item.get("file") or "")
            # map .docx seed names to .txt
            if fname.endswith(".docx"):
                fname_txt = fname[:-5] + ".txt"
            else:
                fname_txt = fname
            path = todo_file_path(group_id, fname_txt) or todo_file_path(group_id, fname)
            if path:
                item["file"] = path.name
                item["absolute_path"] = str(path)
                item["relative_path"] = str(path.relative_to(ROOT)).replace("\\", "/")
            enriched.append(item)
        # ensure group has up to 5 listed files from disk
        if len(enriched) < 5:
            group = next((g for g in _TODO_SPECS if g["group_id"] == group_id), None)
            if group:
                known = {e.get("file") for e in enriched}
                for fname, date, text in group["files"]:
                    if fname in known:
                        continue
                    path = ROOT / group["folder"] / fname
                    if path.is_file():
                        enriched.append(
                            {
                                "date": date,
                                "file": fname,
                                "text": text,
                                "absolute_path": str(path),
                                "relative_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                            }
                        )
                    if len(enriched) >= 5:
                        break
        out[group_id] = enriched
    return out


def search(query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    ensure_synthetic_tree()
    q = (query or "").strip().lower()
    if not q:
        return []
    hits: list[dict[str, Any]] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        blob = f"{path.name} {rel}".lower()
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            content = ""
        score = 0
        if q in path.name.lower():
            score += 5
        if q in rel.lower():
            score += 3
        if q in content.lower():
            score += 2
        tokens = [t for t in q.replace(",", " ").split() if len(t) > 2]
        for tok in tokens:
            if tok in blob or tok in content.lower():
                score += 1
        if score <= 0:
            continue
        snippet = ""
        low = content.lower()
        idx = low.find(q) if q in low else -1
        if idx >= 0:
            start = max(0, idx - 40)
            snippet = content[start : start + 120].replace("\n", " ").strip()
        else:
            snippet = content[:120].replace("\n", " ").strip()
        hits.append(
            {
                "file_name": path.name,
                "relative_path": rel,
                "absolute_path": str(path),
                "snippet": snippet,
                "score": score,
                "corpus_id": "synthetic",
            }
        )
    hits.sort(key=lambda x: (-int(x["score"]), x["file_name"]))
    return hits[: max(1, limit)]


def latest_todo_path(group_id: str) -> Path | None:
    ensure_synthetic_tree()
    for group in _TODO_SPECS:
        if group["group_id"] != group_id:
            continue
        folder = ROOT / group["folder"]
        if not folder.is_dir():
            return None
        files = sorted(
            [p for p in folder.iterdir() if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return files[0] if files else None
    return None


def read_text(absolute_path: str | Path, *, max_chars: int = 6000) -> str:
    path = Path(absolute_path)
    if not path.is_file():
        return ""
    try:
        resolved = path.resolve()
        root = ROOT.resolve()
        if root not in resolved.parents and resolved != root:
            # allow only under synthetic root
            return ""
    except OSError:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except OSError:
        return ""


def tree_summary() -> dict[str, Any]:
    ensure_synthetic_tree()
    folders: dict[str, int] = {}
    files = 0
    for path in ROOT.rglob("*"):
        if path.is_file() and not path.name.startswith("."):
            files += 1
            rel = str(path.parent.relative_to(ROOT)).replace("\\", "/")
            folders[rel] = folders.get(rel, 0) + 1
    return {"root": str(ROOT), "files": files, "folders": folders}
