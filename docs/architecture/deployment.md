# Развёртывание TMKI (MVP / demo)

## Компоненты

```mermaid
flowchart TB
  subgraph client [Клиент]
    Browser[Браузер demo UI]
    Cursor[Cursor IDE + MCP]
  end

  subgraph host [Локальный хост Windows]
    Demo[tmki_demo :8767]
    Runtime[tmki_runtime / tmki_rag]
    Ollama[Ollama :11434]
    Archive[(Архив СКРУ-2)]
  end

  subgraph docker [Docker]
  PG[(Postgres + pgvector :5432)]
  end

  Browser -->|HTTP| Demo
  Demo --> Runtime
  Runtime -->|RAG| PG
  Runtime -->|LLM| Ollama
  Runtime -->|chunks-v2| Archive
  Cursor -->|filesystem MCP| Runtime
```

## Порядок запуска (demo)

```powershell
# 1. Инфраструктура
docker compose up -d postgres
# опционально: docker compose --profile llm up -d

# 2. Переменные (из .env.example)
$env:DATABASE_URL = "postgresql://tmki:tmki_dev@127.0.0.1:5432/tmki"
$env:TMKI_INDEX_BACKEND = "pgvector"

# 3. Индекс регламентов
cd runtime
.\scripts\rebuild_regulations_index.ps1 -Resume

# 4. Demo UI
.\scripts\run_tmki_demo_ui.ps1
# http://127.0.0.1:8767/
```

## Файлы конфигурации

| Файл | Назначение |
|------|------------|
| `docker-compose.yml` | Точка входа Compose |
| `runtime/docker/docker-compose.full.yml` | Postgres, Ollama |
| `.env.example` | Переменные окружения |
| `schemas/tools/providers.registry.json` | Approved tools |
| `schemas/tools/tool-gating.rules.json` | Gating по ролям |

## Production (SHOULD)

- Секреты только через secret manager / `.env` (не в git).
- `TMKI_LLM_PROVIDER=openai` или выделенный Ollama на LAN.
- Security-review: `schemas/security/mvp-security-review.checklist.json`.
- RLS и server-side policy — см. `ORG_MODEL.md`, `07_security_addendum.md`.
