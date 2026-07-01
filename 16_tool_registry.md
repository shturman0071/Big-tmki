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
| `checkPolicy(ctx, tool)` | Tool gating (org/role/env) — см. ниже |
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
| `schemas/tools/tool-gating.rules.json` | Gating по role/env/org |
| `schemas/tools/examples/tool-call-request.example.json` | Пример rag_search |

### Статусы в реестре

| `status` | Поведение |
|----------|-----------|
| `approved` | Доступен по policy |
| `watchlist` | Только `development` (или deny в production) |
| `disabled` | Всегда deny |

## Tool Gating (org / role / env) v0.1

> Связь с матрицей ролей: `ORG_MODEL.md` (Tool gating по ролям).  
> Machine-readable: `schemas/tools/tool-gating.rules.json`

### Алгоритм `checkPolicy()` (MUST)

Выполняется **server-side** до `execute()`. Порядок проверок:

1. **Registry status** — `disabled` → deny; `watchlist` + `env=production` → deny
2. **Org scope** — `company_id` / `project_id` MUST совпадать с `policy_context` (если `same_company` / `same_project`)
3. **Environment** — `policy_context.env` ∈ `env_allowlist` (gate + registry)
4. **Role group** — `project_role` → role_group; MUST ∈ `allow_role_groups`, MUST NOT ∈ `deny_role_groups`
5. **Capability** — запрошенная операция MUST быть ≥ `min_capability` (T_r / T_w из матрицы ORG_MODEL)
6. **Confirmation** — если `requires_confirmation` и нет `confirmed_by_user` → deny
7. **Department scope** — для data tools: применить `default_department_scope` или override по role_group (передаётся в RAG/OCR input)

При deny → `tool_call_denied`, `deny_reason` ∈ `tool-call-response.schema.json`, audit `policy_denied`.

### Role groups (v0.1)

| Group | Примеры `project_role` |
|-------|------------------------|
| `leadership` | Direktor, Projektleiter |
| `engineering_leads` | ГИП, Начальник подразделения |
| `design` | Projektleiter (Design), Generalprojektant |
| `site_ops` | Начальник участка, ОТ и ПБ |
| `contractor` | Подрядчик |
| `it` | ИТ, Связь |

Полный список: `tool-gating.rules.json` → `role_groups`.

### T_w (write tools)

Инструменты с `capabilities: write` или `min_capability: T_w`:

- **MUST**: только `leadership`, `engineering_leads` (по матрице ORG_MODEL)
- **MUST**: `requires_confirmation=true` + audit
- **MUST NOT**: `contractor`, `site_ops`, `finance_hr`

### Файлы policy

| Файл | Назначение |
|------|------------|
| `tool-gating-policy.schema.json` | Схема policy-файла |
| `tool-gating.rules.json` | Правила по `tool_id` и role groups |
| `providers.registry.json` | `env_allowlist`, `min_capability` per tool |

`policy_version` из rules **SHOULD** записываться в Run/Step (`policy_version`).

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
