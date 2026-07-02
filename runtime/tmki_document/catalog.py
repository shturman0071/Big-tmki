from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_HANDBOOK_ROOT = Path(__file__).resolve().parents[2]


def default_templates_dir() -> Path:
    return _HANDBOOK_ROOT / "schemas" / "document" / "examples" / "templates"


def load_template_catalog(catalog_path: Path | None = None) -> dict[str, Any]:
    path = catalog_path or (default_templates_dir() / "catalog.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    templates = data.get("templates") or []
    by_id = {t["template_id"]: t for t in templates if t.get("template_id")}
    return {"catalog_path": str(path), "templates": templates, "by_id": by_id}
