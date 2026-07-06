#!/usr/bin/env python3
"""Сгенерировать skru2_format_lab.json — 20 файлов разных типов из СКРУ-2."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = Path(r"D:\Курсор\СКРУ-2")
OUT = ROOT / "data" / "ground_truth" / "skru2_format_lab.json"
TARGET = 20
MIN_SIZE = 400

# Приоритет: сначала по одному редкому/важному типу, потом добор
EXT_PRIORITY = [
    ".pdf",
    ".docx",
    ".doc",
    ".dwg",
    ".tif",
    ".tiff",
    ".xlsx",
    ".xls",
    ".dxf",
    ".txt",
    ".rtf",
    ".jpg",
    ".jpeg",
    ".png",
    ".csv",
    ".sdr",
    ".ppt",
    ".pptx",
    ".zip",
    ".cdw",
    ".gsi",
    ".log",
    ".msg",
]

QUESTION_HINTS: dict[str, str] = {
    ".pdf": "маркшейдерский акт pdf",
    ".docx": "акт маркшейдерия docx",
    ".doc": "документ word doc",
    ".dwg": "чертеж dwg",
    ".tif": "скан tif маркшейдерия",
    ".tiff": "скан tiff",
    ".xlsx": "таблица xlsx",
    ".xls": "ведомость xls",
    ".dxf": "координаты dxf",
    ".txt": "текстовый файл координаты",
    ".rtf": "документ rtf",
    ".jpg": "схема jpg",
    ".jpeg": "изображение jpeg",
    ".png": "схема png",
    ".csv": "таблица csv",
    ".sdr": "файл sdr",
    ".ppt": "презентация ppt",
    ".pptx": "презентация pptx",
    ".zip": "архив zip",
    ".cdw": "чертеж cdw",
    ".gsi": "файл gsi",
    ".log": "журнал log",
    ".msg": "письмо msg",
}


def _slug(stem: str, n: int) -> str:
    s = re.sub(r"[^\w\-]+", "_", stem, flags=re.UNICODE).strip("_").lower()[:40]
    return s or f"file_{n:02d}"


def _pick_files() -> list[tuple[Path, str]]:
    if not ARCHIVE.is_dir():
        raise SystemExit(f"Архив не найден: {ARCHIVE}")

    by_ext: dict[str, list[Path]] = {}
    for p in ARCHIVE.rglob("*"):
        if not p.is_file():
            continue
        try:
            if p.stat().st_size < MIN_SIZE:
                continue
        except OSError:
            continue
        ext = p.suffix.lower()
        if not ext or ext in {".dwl", ".dwl2", ".bak", ".err"}:
            continue
        by_ext.setdefault(ext, []).append(p)

    for ext in by_ext:
        by_ext[ext].sort(key=lambda x: (len(x.name), str(x)))

    chosen: list[tuple[Path, str]] = []
    used: set[str] = set()

    def add(path: Path) -> bool:
        key = str(path.resolve())
        if key in used:
            return False
        used.add(key)
        chosen.append((path, path.suffix.lower().lstrip(".")))
        return True

    for ext in EXT_PRIORITY:
        if len(chosen) >= TARGET:
            break
        for p in by_ext.get(ext, []):
            if add(p):
                break

    if len(chosen) < TARGET:
        extras = sorted(
            (p for ext, paths in by_ext.items() for p in paths),
            key=lambda x: (x.suffix.lower(), len(x.name), str(x)),
        )
        for p in extras:
            if len(chosen) >= TARGET:
                break
            add(p)

    return chosen[:TARGET]


def main() -> None:
    picked = _pick_files()
    tests: list[dict] = []
    for i, (path, fmt) in enumerate(picked, start=1):
        ext = "." + fmt
        rel = path.relative_to(ARCHIVE).as_posix()
        slug = _slug(path.stem, i)
        hint = QUESTION_HINTS.get(ext, f"документ {fmt}")
        tests.append(
            {
                "id": f"skru_lab_{i:02d}_{slug}",
                "format": fmt,
                "document_relative_path": rel,
                "file_name": path.name,
                "question": f"{hint} {path.stem[:50]}",
                "reference_answer": f"Файл {fmt.upper()}: {path.name}",
            }
        )

    payload = {
        "schema_version": "0.3",
        "corpus_id": "skru-2",
        "description": f"Лаборатория: {len(tests)} файлов разных типов из архива СКРУ-2",
        "tests": tests,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    formats = sorted({t["format"] for t in tests})
    print(f"Wrote {len(tests)} files, {len(formats)} formats -> {OUT}")
    print("formats:", ", ".join(formats))


if __name__ == "__main__":
    main()
