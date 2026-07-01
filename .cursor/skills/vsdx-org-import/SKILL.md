---
name: vsdx-org-import
description: Extracts organizational structure from Visio .vsdx files and updates ORG_MODEL.md. Use when the user references .vsdx org charts, Satimol structure, or asks to import/update org model from Visio.
---

# VSDX Org Import

## Вход

- Файл `.vsdx` (ZIP с XML), например: `Орг Структура Сатимола_проект_10092025.vsdx`
- Целевой файл: `ORG_MODEL.md`

## Извлечение текста

`.vsdx` — ZIP-архив. Текст фигур в `visio/pages/page1.xml`, теги `{visio namespace}Text`.

```python
import zipfile, xml.etree.ElementTree as ET
from pathlib import Path

V = '{http://schemas.microsoft.com/office/visio/2012/main}'
src = Path(r'path\to\file.vsdx')
with zipfile.ZipFile(src) as z:
    root = ET.fromstring(z.read('visio/pages/page1.xml'))

for t in root.iter(f'{V}Text'):
    # собрать text + tail из дочерних элементов
    ...
```

На Windows: писать результат в UTF-8 файл, не полагаться на консоль cp1251.

PowerShell: скопировать `.vsdx` → `.zip`, затем `Expand-Archive`.

## Обновление ORG_MODEL.md

1. Сохранить базовую модель `Company -> Department -> Position -> Employee`.
2. Добавить секции: верхний уровень, ключевые роли (таблица RU/DE/ФИО), подразделения по группам.
3. Указать источник: имя файла + дата схемы.
4. Обновить RLS-маппинг и вакансии (позиции без ФИО).
5. Не включать персональные данные сверх того, что уже на официальной схеме.

## Очистка

- Удалить временные `_vsdx_*.txt` из репозитория.
- **Не коммитить** сами `.vsdx` (см. `.cursorignore`).

## Сверка

После импорта проверить согласованность с `07_security_addendum.md` (RLS-поля).
