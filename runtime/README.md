# TMKI Runtime (MVP v0.1)

Минимальная реализация **Context Builder** и **RAG + server-side RLS** (фильтр до ранжирования).

| Модуль | Назначение |
|--------|------------|
| `tmki_policy` | `policy_context` из org-снимка |
| `tmki_rag` | `rag_search()` — RLS + folder ACL + keyword-score (MVP без pgvector) |
| `tmki_tools` | Tool Registry + gating (`tool-gating.rules.json`) |
| `tmki_loop` | Loop Engine — budget, circuit breaker, state machine |
| `tmki_ingest` | `validate_ingest` / `validate_delete` — gate до OCR pipeline |
| `tmki_admin` | UI + API галочек grant/deny (`python -m tmki_admin`) |
| `tmki_sharepoint` | stub sync ACL SharePoint после изменения grants |
| `tmki_llm` | LLM providers: `stub` (default) / `openai` (`OPENAI_API_KEY`) |
| `tmki_runtime` | `run_mvp()` — end-to-end по `mvp-flow.json` |

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
from tmki_rag import FolderAclContext, load_folder_catalog, load_folder_grants, rag_search
from tmki_policy import build_policy_context, load_org_snapshot

snapshot = load_org_snapshot(Path("../schemas/org/examples/satimol-snapshot.example.json"))
ctx = build_policy_context(snapshot, employee_id="emp_litovsky_d", env="production")
chunks = json.loads(Path("../schemas/document/examples/satimol-chunks.example.json").read_text())["chunks"]
resp = rag_search({"trace_id": "t1", "query": "маркшейдерская съёмка", "policy_context": ctx}, chunks)

# С folder ACL (#21):
folders = load_folder_catalog(Path("../schemas/document/examples/satimol-folders.example.json"))
grants = load_folder_grants(Path("../schemas/org/examples/satimol-folder-grants.example.json"))
acl = FolderAclContext.from_catalog(folders, grants)
resp = rag_search({...}, chunks, folder_acl=acl)
```

Контракты: `search-request` / `search-response` / `chunk-index` в `schemas/document/`.

### MVP Run

```python
from datetime import date
from tmki_policy import build_policy_context, load_org_snapshot
from tmki_runtime import run_mvp
from tmki_runtime.mvp import load_chunks
from pathlib import Path

snapshot = load_org_snapshot(Path("../schemas/org/examples/satimol-snapshot.example.json"))
ctx = build_policy_context(snapshot, employee_id="emp_litovsky_d", env="production", as_of=date(2025, 9, 10))
chunks = load_chunks(Path("../schemas/document/examples/satimol-chunks.example.json"))
result = run_mvp(message="маркшейдерская съёмка", policy_context=ctx, chunks=chunks)
```

### Admin UI (folder grants)

```powershell
cd runtime
python -m tmki_admin
# Открыть http://127.0.0.1:8765/
```
