# Tool Registry

## Назначение

Реестр инструментов фиксирует **разрешенные** категории интеграций (и конкретные варианты), а также минимальные требования к контракту: вход/выход, side-effects, аутентификация, наблюдаемость, ограничения безопасности.

## Контракт инструмента (MUST)

Каждый инструмент в runtime описывается полями `tool-definition.schema.json` (см. `schemas/tools/`).

- **name / version**
- **category**: web / ocr / vector / llm / storage / db / …  
- **capabilities**: read / write / admin / network / filesystem / …
- **inputs/outputs schema**: структурированные поля + ограничения
- **side_effects**: есть/нет, какие именно
- **auth**: тип (api key / oauth / service account), scopes
- **policy hooks**: какие guardrails применяются до/после вызова
- **observability**: какие метрики/логи/трейсы обязаны быть

## Provider Pattern (v0.1)

### Архитектура

```
Loop Engine → Tool Registry → Provider → External Service
                  ↓
            Guardrails (pre/post)
                  ↓
               Audit
```

### Интерфейс провайдера (концептуально)

| Метод | Назначение |
|-------|------------|
| `getDefinition()` | Возвращает `ToolDefinition` из реестра |
| `validateInput(input)` | Server-side validation входа |
| `checkPolicy(ctx, tool)` | Tool gating (org/role/env) — см. #17 |
| `execute(ctx, input)` | Вызов внешнего сервиса |
| `sanitizeOutput(output)` | Перед возвратом в LLM/audit |

**MUST**: каждый провайдер регистрируется по `tool_id`; секреты только через `auth.secret_ref`.

### Жизненный цикл tool call (MUST)

1. `tool_call_requested` — audit до выполнения
2. Lookup `tool_id` в `providers.registry.json`
3. `status=disabled` или watchlist+prod → deny
4. Policy check: env, role (`min_capability`), confirmation
5. Guardrails `pre_call`
6. `execute()` провайдера
7. Guardrails `post_call` + `sanitizeOutput`
8. `tool_call_completed` или `tool_call_denied` / failed step

### Machine-readable реестр

| Файл | Назначение |
|------|------------|
| `schemas/tools/tool-definition.schema.json` | Схема одного инструмента |
| `schemas/tools/tool-call-request.schema.json` | Запрос вызова |
| `schemas/tools/tool-call-response.schema.json` | Ответ / deny |
| `schemas/tools/providers.registry.json` | Approved + watchlist tools |
| `schemas/tools/examples/tool-call-request.example.json` | Пример rag_search |

### Статусы в реестре

| `status` | Поведение |
|----------|-----------|
| `approved` | Доступен по policy |
| `watchlist` | Только `development` (или deny в production) |
| `disabled` | Всегда deny |

## Approved (текущее состояние)

### Web

- SearXNG → `web_searxng`
- Firecrawl → `web_firecrawl`
- Camofox → `web_camofox` (watchlist)

### OCR

- MinerU → `ocr_mineru`
- Mistral OCR 4 → `ocr_mistral`

### Vector / Retrieval

- pgvector → `rag_search`
- zvec (watchlist в `18_technology_watch.md`)

### LLM Providers

- OpenAI → `llm_openai`
- Anthropic → `llm_anthropic`
- Local → TBD

## Правила добавления инструмента (SHOULD)

- описать контракт (см. выше)
- описать риски (данные/сеть/side-effects)
- прописать политику доступа (кто и в каких окружениях может вызывать)
- добавить наблюдаемость (минимум: latency, error rate, usage)
- пройти процесс `18_technology_watch.md` перед добавлением в Approved

## Связанные документы

| Документ | Связь |
|----------|-------|
| `10_ai_runtime.md` | Tool Registry модуль, tool calls, policy |
| `07_security_addendum.md` | tool gating, auth scopes, audit |
| `09_document_processing.md` | OCR, vector retrieval провайдеры |
| `18_technology_watch.md` | Approved / Watchlist, процесс добавления |
| `ORG_MODEL.md` | ограничение доступа по роли/подразделению |
