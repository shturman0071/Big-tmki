# schemas/ — контракты TMKI v0.1

JSON Schema и machine-readable реестры для runtime, документов, оргмодели и инструментов.

## Карта каталогов

| Каталог | Назначение | Ключевые файлы |
|---------|------------|----------------|
| `runtime/` | Run, Step, Event, Loop, MVP flow, audit | `common.schema.json`, `mvp-flow.json`, `audit-event-catalog.json` |
| `document/` | Ingest, OCR, chunks, search, folders | `chunk-index.schema.json`, `search-request.schema.json` |
| `tools/` | Tool Registry, gating, вызовы | `tool-definition.schema.json`, `tool-gating.rules.json`, `providers.registry.json` |
| `org/` | Оргмодель, HR, grants | `employee.schema.json`, `examples/satimol-snapshot.example.json` |
| `security/` | Security-review MVP | `mvp-security-review.checklist.json` |
| `voice/` | Голосовые сессии (v0.3) | `voice-session.schema.json` |

## Быстрый старт для разработчика

1. Оргконтекст: `org/examples/satimol-snapshot.example.json` → `tmki_policy.build_policy_context()`.
2. RAG: `document/examples/satimol-chunks.example.json` + `search-request.schema.json`.
3. Tool call: `tools/examples/tool-call-request.example.json` + `tool-gating.rules.json`.
4. MVP trace: `runtime/examples/mvp-run-trace.example.json` + `runtime/mvp-flow.json`.

## Примеры policy_context

| Файл | Роль |
|------|------|
| `runtime/examples/run.example.json` | Projektleiter |
| `runtime/examples/policy-context-contractor.example.json` | Подрядчик (external) |

## Валидация

```powershell
cd runtime
python -m pytest tests/test_schemas.py -q
```

Pytest-конфиг: `runtime/pyproject.toml` (`[tool.pytest.ini_options]`).

## Docker / окружение

- Compose: `runtime/docker/docker-compose.full.yml` (Postgres+pgvector, Ollama profile `llm`).
- Корневой `docker-compose.yml` — точка входа.
- Переменные: `.env.example` (корень) и `runtime/docker/env.example`.

## Связанные главы

- `10_ai_runtime.md` — runtime и MVP flow
- `16_tool_registry.md` — инструменты
- `ORG_MODEL.md` — RLS и роли
- `07_security_addendum.md` — security-review checklist
