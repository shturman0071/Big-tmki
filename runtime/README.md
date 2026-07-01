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
| `tmki_ocr` | OCR stub/local/HTTP MinerU → Mistral (`TMKI_OCR_MODE`, `pip install -e ".[ocr]"` для PDF) |
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

### Загрузка в pgvector

```powershell
cd runtime/docker
docker compose up -d
$env:DATABASE_URL = "postgresql://tmki:tmki_dev@127.0.0.1:5432/tmki"
$env:TMKI_INDEX_BACKEND = "pgvector"
pip install -e ".[pgvector]"
python scripts/load_regulations_pgvector.py
```

### RAG по импортированным регламентам

```python
from tmki_rag import load_regulations_chunks, rag_search

chunks = load_regulations_chunks()  # artifacts/regulations-import/chunks.json
resp = rag_search({"trace_id": "t1", "query": "промбезопасность", "policy_context": ctx}, chunks)
```

### Re-index с реальным текстом (local OCR)

```powershell
$env:PYTHONPATH = "."
pip install -e ".[ocr]"   # pypdf для PDF
python scripts/reindex_regulations_local.py --checkpoint-every 200
.\scripts\resume_reindex.ps1
.\scripts\watch_reindex.ps1
# → artifacts/regulations-import/chunks-v2.json
python scripts/benchmark_regulations_search.py
python scripts/run_mvp_regulations.py "промбезопасность кран" --hybrid
python scripts/run_mvp_regulations.py "промбезопасность кран" --backend pgvector --hybrid
python scripts/compare_chunks_quality.py
python scripts/reindex_status.py
python scripts/reindex_errors.py
python scripts/run_ocr_http_smoke.py --mock
python scripts/run_legal_corpus_curator.py --dry-run
python scripts/run_legal_corpus_curator.py --apply-ingest
python scripts/run_desktop_sync.py --once --display-name "Литовский Д." --ingest
python scripts/load_regulations_pgvector.py --variant v2
python scripts/load_regulations_pgvector.py --variant v2 --incremental --skip-ivfflat
.\scripts\sync_pgvector_incremental.ps1
```

### Production-like stack (Docker)

```powershell
.\scripts\tmki_stack_up.ps1
# env: docker/env.production.example
python scripts/check_runtime_health.py
.\scripts\setup_pgvector_v2.ps1
python scripts/load_regulations_pgvector.py
```

### TTS (Piper, бесплатный офлайн)

```powershell
pip install -e ".[voice]"
python scripts/download_piper_voice.py
$env:TMKI_TTS_PROVIDER = "piper"
$env:PIPER_VOICE = "ru_RU-denis-medium"
python -c "from tmki_voice import synthesize_speech; print(synthesize_speech('Проверка озвучки'))"
```

### Display cast (TV / планшет по LAN)

```powershell
$env:TMKI_DISPLAY_PROVIDER = "http_cast"
$env:TMKI_CAST_PORT = "8766"
python scripts/run_display_cast.py "ответ ассистента" --target tv
# Откройте URL на TV-браузере в той же сети
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
