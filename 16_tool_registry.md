# Tool Registry

## Назначение

Реестр инструментов фиксирует **разрешенные** категории интеграций (и конкретные варианты), а также минимальные требования к контракту: вход/выход, side-effects, аутентификация, наблюдаемость, ограничения безопасности.

## Контракт инструмента (MUST)

Каждый инструмент в runtime описывается следующими полями (концептуально):

- **name / version**
- **category**: web / ocr / vector / llm / storage / db / …  
- **capabilities**: read / write / admin / network / filesystem / …
- **inputs/outputs schema**: структурированные поля + ограничения
- **side_effects**: есть/нет, какие именно
- **auth**: тип (api key / oauth / service account), scopes
- **policy hooks**: какие guardrails применяются до/после вызова
- **observability**: какие метрики/логи/трейсы обязаны быть

## Approved (текущее состояние)

### Web

- SearXNG
- Firecrawl
- Camofox

### OCR

- MinerU
- Mistral OCR 4

### Vector / Retrieval

- pgvector
- zvec (watchlist в `18_technology_watch.md`)

### LLM Providers

- OpenAI
- Anthropic
- Local

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
