# TMKI Runtime (MVP v0.1)

Минимальная реализация **Context Builder**: сбор `policy_context` из org-снимка (server-side).

## Запуск тестов

```powershell
cd runtime
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Использование

```python
from pathlib import Path
from tmki_policy import build_policy_context, load_org_snapshot

snapshot = load_org_snapshot(Path("../schemas/org/examples/satimol-snapshot.example.json"))
ctx = build_policy_context(snapshot, employee_id="emp_litovsky_d", env="production")
```

Контракт: `schemas/runtime/common.schema.json#/$defs/policyContext`, логика — `ORG_MODEL.md`.
