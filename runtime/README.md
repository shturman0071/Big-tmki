# TMKI Runtime (MVP v0.1)

Минимальная реализация **Context Builder** и **RAG + server-side RLS** (фильтр до ранжирования).

| Модуль | Назначение |
|--------|------------|
| `tmki_policy` | `policy_context` из org-снимка |
| `tmki_rag` | `rag_search()` — RLS + keyword-score (MVP без pgvector) |

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

### RAG (MVP)

```python
import json
from pathlib import Path
from tmki_rag import rag_search
from tmki_policy import build_policy_context, load_org_snapshot

snapshot = load_org_snapshot(Path("../schemas/org/examples/satimol-snapshot.example.json"))
ctx = build_policy_context(snapshot, employee_id="emp_litovsky_d", env="production")
chunks = json.loads(Path("../schemas/document/examples/satimol-chunks.example.json").read_text())["chunks"]
resp = rag_search({"trace_id": "t1", "query": "маркшейдерская съёмка", "policy_context": ctx}, chunks)
```

Контракты: `search-request` / `search-response` / `chunk-index` в `schemas/document/`.
