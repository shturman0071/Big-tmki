from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TodoItem:
    text: str
    assignee_hint: str | None = None


_TODO_PATTERNS = (
    r"(?:нужно|надо|добавь|запиши|поставь задачу)[:\s]+(.+)",
    r"(?:todo|туду)[:\s]+(.+)",
)


def extract_todo_items(transcript: str) -> list[TodoItem]:
    """Извлечь to-do из транскрипта планёрки/голосовой команды (#49)."""
    items: list[TodoItem] = []
    for line in transcript.splitlines():
        line = line.strip()
        if not line:
            continue
        for pattern in _TODO_PATTERNS:
            m = re.search(pattern, line, flags=re.IGNORECASE)
            if m:
                items.append(TodoItem(text=m.group(1).strip()))
                break
    return items
