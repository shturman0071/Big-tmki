# Document Intelligence Layer

Primary: MinerU
Fallback: Mistral OCR 4

## Цель

Слой Document Intelligence превращает “сырые” документы (PDF/сканы/изображения) в нормализованный, цитируемый и индексируемый набор артефактов для RAG/поиска: Markdown/текст, таблицы/изображения (если применимо), метаданные, чанки и эмбеддинги.

## Поддерживаемые входы (MAY расширяться)

- PDF (текстовый / скан)
- изображения (PNG/JPG)
- офисные форматы (если есть конвертация в PDF/изображения на входе пайплайна)

## Выходы (контракт)

- `doc_id` (стабильный идентификатор)
- `doc_manifest` (структура документа, версии, контрольные суммы)
- `markdown` (нормализованный текст)
- `assets` (картинки/страницы/вложения при необходимости)
- `metadata` (см. ниже)
- `chunks[]` (чанки с координатами/смещениями)
- `embeddings[]` (по чанкам)

## Метаданные (MUST)

- **provenance**: источник (url/path), загрузчик (user/service), время
- **classification**: уровень доступа/конфиденциальности (для фильтрации)
- **language**: язык(и) документа
- **content_hash**: хэш содержимого (для дедупликации)
- **parser_version**: версия парсера/OCR (MinerU/Mistral OCR 4)
- **errors/warnings**: деградации, пропуски страниц, низкая уверенность OCR

## Pipeline

Pipeline:
Document -> OCR -> Markdown -> Metadata -> Chunking -> Embeddings -> Vector Search

### 1) Ingest

- **Вход**: бинарный документ + базовые поля (org/project, uploader, access label).
- **MUST**: вычислить `content_hash` и проверить дедупликацию.
- **Schema**: `schemas/document/ingest-request.schema.json`, `schemas/document/ingest-response.schema.json`

#### Алгоритм ingest (MUST)

1. **Валидация** — mime_type, size limit (default max 100 MB), `policy_context`, `classification`.
2. **Вычисление hash** — `content_hash = "sha256:" + SHA-256(raw_bytes)`.
3. **Dedup lookup** — ключ: `dedup_key = {company_id}:{project_id}:{content_hash}`.
4. **Решение** — см. таблицу ниже.
5. **Audit** — `document_ingested` или skip с `dedup.action` (см. `audit-event-catalog.json`).

#### Дедупликация по `content_hash`

| Условие | `ingest_status` | Действие | `dedup.action` |
|---------|-----------------|----------|----------------|
| Hash не найден в проекте | `accepted` → `processing` | Новый `doc_id`, запуск pipeline | `none` |
| Hash найден, тот же `classification` | `duplicate` | Вернуть `matched_doc_id`, pipeline **не** запускать | `skipped_processing` |
| Hash найден, другой `classification` | `duplicate` | Вернуть `matched_doc_id` + audit warning; re-index filters MAY обновиться† | `linked_existing` |
| `force_reprocess=true` (admin) | `accepted` | Новый pipeline job на существующий `doc_id` | `reprocessed` |
| `idempotency_key` повторён | `duplicate` или `processing` | Идемпотентный ответ первого запроса | `skipped_processing` |
| Валидация не пройдена | `rejected` | 4xx, без записи doc | — |

† Обновление `classification` на существующем doc — отдельная admin-операция (SHOULD), не через обычный ingest.

#### Идемпотентность (MUST)

- Повторный ingest с тем же `content_hash` в том же `project_id` **MUST NOT** создавать второй `doc_id`.
- Повтор с тем же `idempotency_key` **MUST** возвращать тот же результат (safe retry).
- Pipeline stages после ingest **MUST** быть идемпотентны по `doc_id` + `content_hash` + `parser_version`.

#### `doc_id` (MUST)

- Формат: `doc_{slug}` или UUID — стабилен после первого ingest.
- **MUST NOT** переиспользовать `doc_id` для другого `content_hash` (кроме явного versioning).

#### Поля ingest request (обязательные)

| Поле | Источник |
|------|----------|
| `policy_context` | `ORG_MODEL.md` — `company_id`, `project_id`, `department_id`, `employee_id`, `project_role` |
| `classification` | `access_label` для RLS |
| `trace_id` | Связь с Audit (`10_ai_runtime.md`) |

#### Ошибки ingest

| Код | Причина |
|-----|---------|
| `INGEST_FILE_TOO_LARGE` | Превышен size limit |
| `INGEST_UNSUPPORTED_MIME` | Тип не в allowlist |
| `INGEST_CLEARANCE_DENIED` | `classification` выше `user.clearance` |
| `INGEST_DEDUP_CONFLICT` | Редкий конфликт idempotency (retry с другим телом) |

### 2) OCR / Extract

- **Primary**: MinerU
- **Fallback**: Mistral OCR 4
- **Schema**: `schemas/document/ocr-result.schema.json`

#### Порядок провайдеров (MUST)

1. Всегда начинать с **MinerU** (`provider=mineru`).
2. При срабатывании fallback-условий — **одна** попытка **Mistral OCR 4**.
3. Если fallback тоже failed → `ocr_status=failed`, pipeline останавливается с partial artifacts (если есть).

#### Условия fallback (MUST)

| Условие | `fallback_reason` | Порог (default) |
|---------|-------------------|-----------------|
| Таймаут MinerU | `primary_timeout` | 120 s на документ (production) |
| Ошибка API/парсера MinerU | `primary_error` | любой non-retryable error |
| Средняя уверенность ниже порога | `low_confidence` | `avg_confidence < 0.65` |
| Извлечённый текст пуст/слишком мал | `empty_text` | `< 50` символов при `page_count > 1` |
| Слишком много пустых страниц | `partial_pages` | `> 30%` страниц без текста |

**MUST**: записывать `primary_attempt` и `fallback_reason` в `ocr-result` и `metadata.errors/warnings`.

#### SLA / таймауты (SHOULD)

| Параметр | Production | Development |
|----------|------------|-------------|
| MinerU timeout | 120 s | 180 s |
| Mistral OCR 4 timeout | 180 s | 240 s |
| Max pages per job | 500 | 500 |
| Retry на primary | 1 (только transient errors) | 2 |

#### Качество и статусы

| `ocr_status` | Критерий | Дальше по pipeline |
|--------------|----------|-------------------|
| `completed` | Все страницы OK или допустимые warnings | → Normalize to Markdown |
| `partial` | Есть пропуски страниц / warnings, но текст пригоден | → Markdown + `warnings` |
| `failed` | Нет пригодного текста после fallback | Stop, audit error |

**SHOULD**: `avg_confidence` и per-page `confidence` сохранять в `ocr-result.pages[]`.

#### `parser_version` (MUST)

Формат: `{provider}@{version}` — примеры:

- `mineru@2.1.0`
- `mistral-ocr-4@2026-06`

При fallback финальный `parser_version` **MUST** отражать фактически использованный провайдер.

#### Метрики и audit (MUST)

| Метрика | Описание |
|---------|----------|
| `ocr_duration_ms` | Время по провайдеру |
| `ocr_fallback_rate` | Доля `fallback_used=true` |
| `ocr_partial_rate` | Доля `ocr_status=partial` |
| `ocr_error_rate` | Доля `ocr_status=failed` |

Audit: `document_ingested` payload **MUST** включать `parser_version`, `fallback_used`, `warnings_count` (см. `audit-event-catalog.json`).

#### Коды ошибок OCR

| Код | Описание |
|-----|----------|
| `OCR_PRIMARY_TIMEOUT` | MinerU timeout |
| `OCR_PRIMARY_ERROR` | MinerU error |
| `OCR_LOW_CONFIDENCE` | Ниже порога уверенности |
| `OCR_EMPTY_TEXT` | Пустой результат |
| `OCR_FALLBACK_FAILED` | Оба провайдера не справились |
| `OCR_PAGE_LIMIT_EXCEEDED` | Слишком много страниц |

### 3) Normalize to Markdown

- **MUST**: сохранять структуру (заголовки, списки) насколько возможно.
- **SHOULD**: нормализовать переносы строк/пробелы, убирать “мусор” OCR.
- **MUST**: сохранять карту соответствий “страница → диапазоны текста”, чтобы можно было цитировать.

### 4) Metadata enrichment

- извлечение: автор/дата (если есть), темы/теги, тип документа
- связывание с орг-моделью/проектом при наличии (см. `ORG_MODEL.md`)

### 5) Chunking

- **MUST**: чанки должны быть **цитируемыми**: включать `doc_id`, `page`, `start_offset`, `end_offset`.
- **SHOULD**: chunking учитывать структуру Markdown (не резать посреди заголовка/таблицы).
- **SHOULD**: задавать лимиты: max tokens/символов на чанк, overlap.

### 6) Embeddings

- **MUST**: версия модели эмбеддингов фиксируется в `doc_manifest`.
- **SHOULD**: пересчитывать эмбеддинги при изменении модели/параметров chunking.

### 7) Index / Vector Search

- индекс хранит: embedding + поля фильтрации (org, project, classification, language) — см. `ORG_MODEL.md`, `07_security_addendum.md`.
- **MUST**: фильтрация доступа применяется **до** выдачи результатов (server-side).
- vector store: см. `16_tool_registry.md` (pgvector — approved).

## JSON Schema (v0.1)

| Контракт | Schema | Пример |
|----------|--------|--------|
| Ingest Request | `schemas/document/ingest-request.schema.json` | `schemas/document/examples/ingest-request.example.json` |
| Ingest Response | `schemas/document/ingest-response.schema.json` | `schemas/document/examples/ingest-response-duplicate.example.json` |
| OCR Result | `schemas/document/ocr-result.schema.json` | `schemas/document/examples/ocr-result-fallback.example.json` |

## SLA и деградация (SHOULD)

- **таймауты**: на OCR и на полный пайплайн
- **частичные результаты**: допустимы, но должны сопровождаться `warnings`
- **повторная обработка**: идемпотентна по `doc_id/content_hash`

## Наблюдаемость (MUST)

- метрики: время по стадиям, доля fallback, доля ошибок, размер документов/чанков
- логи: trace id на документ, причины деградаций (см. `10_ai_runtime.md`, Audit)

## Связанные документы

| Документ | Связь |
|----------|-------|
| `10_ai_runtime.md` | Document Intelligence, RAG, Audit/trace |
| `07_security_addendum.md` | server-side фильтрация, classification |
| `16_tool_registry.md` | OCR (MinerU, Mistral OCR 4), pgvector |
| `ORG_MODEL.md` | org/project поля в metadata и индексе |
| `18_technology_watch.md` | статус MinerU, Mistral OCR 4, zvec |
