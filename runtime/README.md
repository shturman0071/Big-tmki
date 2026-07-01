# TMKI Runtime (MVP v0.1)

Минимальная реализация **Context Builder** и **RAG + server-side RLS** (фильтр до ранжирования).

| Модуль | Назначение |
|--------|------------|
| `tmki_policy` | `policy_context` из org-снимка |
| `tmki_rag` | `rag_search()` + `ChunkIndex` / `VectorChunkIndex` / pgvector (`TMKI_INDEX_BACKEND`, `TMKI_EMBEDDING_PROVIDER`) |
| `tmki_runtime` | `run_mvp()` — end-to-end по `mvp-flow.json` |
| `tmki_tools` | Tool Registry + gating (`tool-gating.rules.json`) |
| `tmki_loop` | Loop Engine — budget, circuit breaker, state machine |
| `tmki_ingest` | gate / dedup / pipeline / `scan_regulations_archive` / `import_regulations_batch` |
| `tmki_ocr` | OCR stub/HTTP MinerU → Mistral (`TMKI_OCR_MODE`, `MINERU_API_URL`) |
| `tmki_admin` | UI + API галочек grant/deny (`python -m tmki_admin`) |
| `tmki_sharepoint` | stub + Graph adapter (`TMKI_GRAPH_DRY_RUN`, production resolve→invite/revoke) |
| `tmki_llm` | LLM: `stub` / `openai` / `ollama` (`OLLAMA_BASE_URL`, `OLLAMA_MODEL`) |

## Запуск тестов

```powershell
cd runtime
python -m pip install -e ".[dev]"
python -m pytest -q
```

### Postgres + pgvector (local)

```powershell
cd runtime/docker
docker compose up -d
# Скопировать env: cp env.example ../.env.local (или export вручную)
$env:DATABASE_URL = "postgresql://tmki:tmki_dev@127.0.0.1:5432/tmki"
$env:TMKI_INDEX_BACKEND = "pgvector"
pip install -e ".[pgvector]"
python scripts/pgvector_smoke.py
```

### Импорт регламентов (#6 MVP)

```python
from pathlib import Path
from tmki_ingest import scan_regulations_archive, import_regulations_batch, DedupStore
from tmki_rag import ChunkIndex

manifest = scan_regulations_archive(Path("D:/ТМКИ оригнал"), compute_hash=True)
# manifest["stats"] — ingest_candidate / catalog_only / skip

result = import_regulations_batch(
    Path("D:/ТМКИ оригнал"),
    policy_context=ctx,
    classification="restricted",
    folder_id="folder_ms_open",
    folder_acl=acl,
    dedup_store=DedupStore(),
    index=ChunkIndex(),
    limit=10,
)
```

Контракт manifest: `schemas/document/regulations-catalog.schema.json`.

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

# Ingest → index → search:
from tmki_ingest import DedupStore, ingest_and_index
from tmki_rag import ChunkIndex

index = ChunkIndex()
ingest_and_index(request, index, folder_acl=acl, dedup_store=DedupStore(), raw_bytes=b"...")
resp = rag_search({...}, index.list(), folder_acl=acl)
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

### MVP с vector index и Ollama

```python
from tmki_rag import VectorChunkIndex

index = VectorChunkIndex()
index.add(chunks)
result = run_mvp(
    message="маркшейдерская съёмка",
    policy_context=ctx,
    chunks=[],
    index=index,
    use_hybrid_search=True,
    llm_provider="ollama",  # TMKI_LLM_PROVIDER=ollama, OLLAMA_BASE_URL
)
```

### Admin UI (folder grants)

```powershell
cd runtime
python -m tmki_admin
# Открыть http://127.0.0.1:8765/
```
