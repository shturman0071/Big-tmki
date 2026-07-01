# Roadmap — Big-tmki / TMKI Engineering Handbook

План работ по фазам. Каждый пункт ниже — кандидат в GitHub Issue.

**Репозиторий:** <https://github.com/shturman0071/Big-tmki>

## Метки (labels)

| Label | Назначение |
|-------|------------|
| `phase-0` | Фундамент, процессы |
| `phase-1` | Документация хэндбука |
| `phase-2` | Модель данных и доступы |
| `phase-3` | Контракты runtime |
| `phase-4` | Document Intelligence |
| `phase-5` | Tool Registry / провайдеры |
| `phase-6` | MVP AI Runtime |
| `security` | Security, RLS, guardrails |
| `runtime` | AI Runtime |
| `docs` | Документация |

---

## Phase 0 — Фундамент

### #1 [phase-0] [docs] Синхронизировать перекрёстные ссылки между главами

**Статус:** done (в коммите с ROADMAP)

- Добавлены секции «Связанные документы» во все главы
- Уточнены ссылки runtime ↔ security ↔ org ↔ tools

**Критерий:** нет «висящих» отсылок «см. runtime» без имени файла.

---

### #2 [phase-0] [docs] Закрепить владельцев и процесс апрува хэндбука

**Статус:** done (v0.1 — `AGENTS.md` §Владельцы и апрув, ссылка в `README.md`)

- Матрица owner по главам (роли Сатимол)
- Апрув MUST, триггеры security-review, когда обновлять README

---

### #3 [phase-0] Установить GitHub CLI и завести labels

**Статус:** done — `gh` v2.95.0, labels, 19 issues на GitHub (7 open, 12 closed)

```powershell
winget install GitHub.cli
# Перезапустите терминал ИЛИ обновите PATH в текущей сессии:
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
& "C:\Program Files\GitHub CLI\gh.exe" auth login -h github.com -p https -w
.\scripts\create-github-issues.ps1 -IncludeDone
```

Issues: <https://github.com/shturman0071/Big-tmki/issues>

---

## Phase 1 — Документация

### #4 [phase-1] [docs] Дописать `13_ai_skills_registry.md` — owners

**Статус:** done (v0.1 — owners по ORG_MODEL, example на skill)

---

### #5 [phase-1] [docs] Детализировать `18_technology_watch.md` — карточки Approved

**Статус:** done (v0.1 — таблица карточек Approved + Watchlist)

---

### #6 [phase-1] [docs] Импорт регламентов из `ТМКИ оригнал`

**Статус:** MVP (v0.2) — `scan_regulations_archive()` + `import_regulations_batch()` в `tmki_ingest/regulations.py`; полный архив ~1200+ файлов — backlog

---

## Phase 2 — Доступы

### #7 [phase-2] [security] Матрица «роль → права → RLS»

**Статус:** done (v0.2 — `ORG_MODEL.md`: матрица + решения по access_label, Design scope, group_admin, подрядчики)

На базе `ORG_MODEL.md` (проект Сатимол). Выход: таблица role × resource × action × RLS-поля.

---

### #8 [phase-2] [security] Схема сущностей org model

**Статус:** done (v0.1 — `schemas/org/`, пример `satimol-snapshot.example.json`, §Схема сущностей в `ORG_MODEL.md`)

`company`, `department`, `position`, `employee`, `project`, `project_role`, `assignment`.

---

### #9 [phase-2] [docs] Актуализировать вакансии оргсхемы (10.09.2025)

**Статус:** done (v0.1 — таблица вакансий в `ORG_MODEL.md`, `positions` в `satimol-snapshot.example.json`)

Сверка с HR/проектом: что закрыто, что открыто.

---

## Phase 3 — Контракты runtime

### #10 [phase-3] [runtime] JSON-схемы Run / Step / Event

**Статус:** done (v0.1 в `schemas/runtime/`)

Формализация контрактов из `10_ai_runtime.md`.

---

### #11 [phase-3] [runtime] State machine Loop Engine

**Статус:** done (v0.1 в `10_ai_runtime.md` + `schemas/runtime/loop-state.schema.json`)

Лимиты шагов, таймауты, budget, circuit breaker, stop conditions.

---

### #12 [phase-3] [security] Каталог audit events

**Статус:** done (v0.1 — `schemas/runtime/audit-event-catalog.json`, раздел Audit в `10_ai_runtime.md`)

`event_type`, severity, санитизация payload, связь с `trace_id`.

---

## Phase 4 — Document Intelligence

### #13 [phase-4] [runtime] Ingest + dedup по `content_hash`

**Статус:** done (v0.1 — `09_document_processing.md`, `schemas/document/`)

По `09_document_processing.md`, поля из `ORG_MODEL.md`.

---

### #14 [phase-4] [runtime] OCR pipeline MinerU → fallback Mistral OCR 4

**Статус:** done (v0.1 — `09_document_processing.md`, `schemas/document/ocr-result.schema.json`)

Метрики fallback, warnings в metadata.

---

### #15 [phase-4] [security] Индексация с server-side фильтрацией доступа

**Статус:** done (v0.1 — `09_document_processing.md` §7, `schemas/document/search-*.schema.json`)

pgvector + RLS-поля до выдачи в RAG.

---

## Phase 5–6 — Интеграция (backlog)

### #16 [phase-5] [runtime] Каркас Tool Registry + provider pattern

**Статус:** done (v0.1 — `16_tool_registry.md`, `schemas/tools/`)

### #17 [phase-5] [security] Tool gating по org/role/env

**Статус:** done (v0.1 — `16_tool_registry.md` §Tool Gating, `schemas/tools/tool-gating.rules.json`)

---

### #18 [phase-6] [runtime] MVP: Context → RAG → Loop → Judge → Audit

**Статус:** done (v0.1 — `10_ai_runtime.md` §MVP End-to-End, `schemas/runtime/mvp-flow.json`)

### #19 [phase-6] [security] Security-review перед MVP-релизом

**Статус:** done (v0.1 — `07_security_addendum.md` §MVP Security Review, `schemas/security/`)

---

### #20 [phase-0] CI: markdown lint + secret scan

**Статус:** done (v0.1 — `.github/workflows/handbook-ci.yml`, `.markdownlint.jsonc`, `.gitleaks.toml`)

- `markdown-lint` — markdownlint-cli2 на все `*.md`
- `secret-scan` — gitleaks с allowlist для schema/docs references

---

## Текущий фокус (эта неделя)

1. ~~#1 Синхронизация ссылок~~ ✅
2. ~~#7 Матрица роль → права → RLS~~ ✅ (DRAFT v0.1)
3. ~~#10 JSON-схемы Run/Step/Event~~ ✅ (v0.1)
4. ~~#11 State machine Loop Engine~~ ✅ (v0.1)
5. ~~#12 Каталог audit events~~ ✅ (v0.1)
6. ~~#13 Ingest + dedup (Document Intelligence)~~ ✅ (v0.1)
7. ~~#14 OCR pipeline MinerU + fallback~~ ✅ (v0.1)
8. ~~#15 Индексация с server-side фильтрацией~~ ✅ (v0.1)
9. ~~#16 Tool Registry каркас~~ ✅ (v0.1)
10. ~~#17 Tool gating по org/role/env~~ ✅ (v0.1)
11. ~~#18 MVP runtime end-to-end~~ ✅ (v0.1)
12. ~~#19 Security-review перед MVP-релизом~~ ✅ (v0.1)
13. ~~#20 CI: markdown lint + secret scan~~ ✅ (v0.1)
14. ~~#3 Установить gh + создать issues на GitHub~~ ✅
15. ~~#2 Закрепить владельцев и процесс апрува хэндбука~~ ✅ (v0.1)
16. ~~#4 Owners в 13_ai_skills_registry.md~~ ✅ (v0.1)
17. ~~#5 Карточки Approved в 18_technology_watch.md~~ ✅ (v0.1)
18. ~~#6 Импорт регламентов~~ — полный stub-импорт ✅ (8056 chunks локально)
19. ~~#7 RLS open questions (Сатимол)~~ ✅ (v0.2)
20. ~~#8 Схема сущностей org model~~ ✅ (v0.1)
21. ~~#9 Актуализировать вакансии оргсхемы~~ ✅ (v0.1)
22. ~~#21 Folder grants~~ ✅
23. ~~#22–#24 ingest dedup, LLM, CI pytest~~ ✅
24. ~~#25 OCR stub pipeline~~ ✅
25. ~~#26 SharePoint Graph adapter (каркас)~~ ✅
26. ~~#27 Ollama LLM provider~~ ✅
27. ~~#28 Graph permissions dry_run operations~~ ✅
28. ~~#29 ChunkIndex + ingest_and_index~~ ✅
29. ~~#30 Graph production permissions (resolve + invite/revoke)~~ ✅
30. ~~#31 OCR HTTP providers (MinerU/Mistral)~~ ✅
31. ~~#32 VectorChunkIndex + pgvector factory~~ ✅
32. ~~#33 Embeddings API providers (local/openai/ollama)~~ ✅
33. ~~#34 pgvector cosine search~~ ✅
34. ~~#35 E2E MVP с Ollama + vector index~~ ✅
35. ~~#36 Postgres+pgvector deploy (docker-compose)~~ ✅
36. ~~#6 Полный stub-импорт архива (8056 chunks)~~ ✅
37. ~~#37 Regulations RAG + load в pgvector + IVFFlat~~ ✅
38. ~~#38 Local text extraction + re-index~~ ✅
39. ~~#39 Regulations MVP + search benchmark + chunks-v2 auto~~ ✅
40. ~~#40 Production stack + re-index hardening~~ ✅ (docker-compose.full, health check, pypdf noise fix, skip ~$ temp)
41. ~~#41 Re-index progress + PDF hardening~~ ✅ (max_pages, heartbeat progress, reindex_status, check_ocr_http)
42. **Следующий фокус:** завершить re-index → chunks-v2; load pgvector; HTTP MinerU/Mistral
43. ~~#45 Desktop sync~~ ✅ | ~~#46 Legal Corpus Curator~~ ✅ | ~~#47 Document policy~~ ✅
44. ~~#43–#50~~ ✅ MVP | **#51:** `setup_pgvector_v2.ps1`, partial load v2, weekly legal curator

---

## Phase 7 — Product v0.3 (рабочее место и нормативная база)

### #43 [phase-6] [runtime] Сетевая политика LLM (local + internet)

**Статус:** MVP (v0.3) — `llm_ollama` в registry + tool-gating; OpenAI/Ollama через `TMKI_LLM_PROVIDER`

### #44 [phase-2] [runtime] Папка сотрудника на рабочем столе

**Статус:** MVP (v0.3) — `provision_employee_desktop()`, `provision_employee_desktop.py`

### #45 [phase-4] [runtime] Desktop sync agent (5 с → локальный сервер)

**Статус:** MVP (v0.3) — `tmki_desktop_sync/`, `run_desktop_sync.py`

- Watch folder → server copy → ingest; `TMKI_DESKTOP_SYNC_INTERVAL_SEC=5`
- **Критерий:** `runtime/tmki_desktop_sync/`; audit `desktop_sync_file_uploaded`

### #46 [phase-4] [runtime] Внешняя нормативная база РФ + Legal Corpus Curator

**Статус:** MVP (v0.3) — `tmki_legal/`, `run_legal_corpus_curator.py`

- Первичная загрузка 16+ актов; еженедельный мониторинг официальных сайтов
- **Критерий:** агент diff → ingest → notify; skill в `13_ai_skills_registry.md`

### #47 [phase-4] [docs] Политика создания документов

**Статус:** MVP (v0.3) — `tmki_ingest/document_policy.py`, `document-creation-policy.schema.json`

- Внутренние шаблоны; договоры — проверка по РФ всегда; прочее — только по запросу
- **Критерий:** guardrail в runtime document author flow

### #48 [phase-2] [security] HR-карточка: голос и антропометрия

**Статус:** MVP (v0.3) — `tmki_hr/cards.py`, consent gate, изолированное хранилище

### #49 [phase-6] [runtime] Voice STT: to-do и планёрки

**Статус:** MVP (v0.3) — `tmki_voice/stt.py`, `meeting.py`, `TMKI_STT_PROVIDER=stub|whisper`

### #50 [phase-6] [runtime] TTS Piper + вывод на устройства

**Статус:** MVP (v0.3) — `tmki_voice/tts.py`, `display.py` (stub/browser/http_cast LAN); Chromecast/Miracast — backlog

### #53 [phase-6] [runtime] TV cast HTTP (LAN)

**Статус:** MVP (v0.3) — `tmki_voice/cast_server.py`, `HttpCastDisplayProvider`, `run_display_cast.py`

### #51 [phase-4] [runtime] pgvector v2 partial load + ops scripts

**Статус:** MVP (v0.3) — `setup_pgvector_v2.ps1`, `weekly_legal_corpus.ps1`, `resume_reindex.ps1`, re-index stats в health check

### #52 [phase-4] [runtime] Legal curator → ingest pipeline

**Статус:** MVP (v0.3) — `tmki_legal/ingest_hook.py`, `--apply-ingest` в `run_legal_corpus_curator.py`

### #54 [phase-4] [runtime] Incremental pgvector sync + re-index progress

**Статус:** MVP (v0.3) — `--incremental` в `load_regulations_pgvector.py`, `sync_pgvector_incremental.ps1`, `total_candidates` в state

### #55 [phase-4] [runtime] HTTP OCR smoke + re-index error report

**Статус:** MVP (v0.3) — `run_ocr_http_smoke.py`, `reindex_errors.py`, `recent_errors` в state

### #56 [phase-4] [runtime] Re-index heartbeat + MVP pgvector backend

**Статус:** MVP (v0.3) — `reindex-heartbeat.json`, `--backend pgvector` в `run_mvp_regulations.py`

---

## Phase 4.5 — Runtime hardening (v0.2)

### #22 [phase-4] [runtime] Ingest dedup + accept_ingest pipeline

**Статус:** done (v0.1 — `tmki_ingest/dedup.py`, `pipeline.py`)

### #23 [phase-5] [runtime] LLM provider pattern (stub + OpenAI)

**Статус:** done (v0.1 — `tmki_llm/providers.py`, env `TMKI_LLM_PROVIDER`)

### #24 [phase-0] [runtime] CI: pytest для `runtime/`

**Статус:** done — job `runtime-tests` в `.github/workflows/handbook-ci.yml`

---

### #25 [phase-4] [runtime] OCR stub pipeline (MinerU → Mistral)

**Статус:** done (v0.1 — `tmki_ocr/ocr.py`, `process_document` в `tmki_ingest`)

### #26 [phase-2] [runtime] SharePoint Graph adapter (каркас)

**Статус:** done (v0.1 — `tmki_sharepoint/graph.py`, env `AZURE_*`); production driveItem permissions — backlog

### #27 [phase-5] [runtime] Ollama LLM provider

**Статус:** done (v0.2 — `OllamaLlmProvider`, env `TMKI_LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`)

### #28 [phase-2] [runtime] Graph permissions operations (dry_run)

**Статус:** done (v0.2 — `_build_operation` invite/revoke, `TMKI_GRAPH_DRY_RUN=1` по умолчанию)

### #29 [phase-4] [runtime] ChunkIndex + ingest → RAG

**Статус:** done (v0.2 — `tmki_rag/index.py`, `ingest_and_index()` в pipeline)

### #30 [phase-2] [runtime] Graph production permissions API

**Статус:** done (v0.2 — resolve driveItem → invite/revoke, injectable HTTP для тестов)

### #31 [phase-4] [runtime] OCR HTTP providers (MinerU/Mistral)

**Статус:** done (v0.2 — `TMKI_OCR_MODE=http`, `MINERU_API_URL`, `MISTRAL_OCR_API_URL`)

### #32 [phase-4] [runtime] VectorChunkIndex + pgvector factory

**Статус:** done (v0.2 — `VectorChunkIndex`, `get_chunk_index()`, `PgVectorChunkIndex` с fallback)

### #33 [phase-4] [runtime] Embeddings API providers

**Статус:** done (v0.2 — `TMKI_EMBEDDING_PROVIDER=local|openai|ollama`)

### #34 [phase-4] [runtime] pgvector cosine search

**Статус:** done (v0.2 — SQL `<=>` при наличии extension, fallback in-memory)

### #35 [phase-6] [runtime] E2E MVP с Ollama + vector index

**Статус:** done (v0.2 — `run_mvp(llm_provider=ollama, index=..., use_hybrid_search=True)`)

### #36 [phase-4] [runtime] Postgres+pgvector deploy

**Статус:** done (v0.2 — `runtime/docker/docker-compose.yml`, `init.sql`, `scripts/pgvector_smoke.py`)

### #6 [phase-1] [runtime] Импорт регламентов — scanner + batch

**Статус:** done (v0.2) — полный stub-прогон 10 089 кандидатов → 8056 chunks (`artifacts/regulations-import/`)

### #37 [phase-4] [runtime] Regulations RAG + pgvector load

**Статус:** done (v0.2 — `load_regulations_chunks`, `load_regulations_pgvector.py`, IVFFlat после bulk load)

### #38 [phase-4] [runtime] Local text extraction + re-index

**Статус:** done (v0.2 — `TMKI_OCR_MODE=local`, txt/docx/pdf+pypdf, `reindex_regulations_local.py` → `chunks-v2.json`)

### #39 [phase-6] [runtime] Regulations MVP + search benchmark

**Статус:** done (v0.2 — `run_mvp_regulations.py`, `benchmark_regulations_search.py`, `resolve_regulations_chunks_path`)

### #40 [phase-6] [runtime] Production stack + re-index hardening

**Статус:** done (v0.2 — `docker-compose.full.yml`, `env.production.example`, `check_runtime_health.py`, `compare_chunks_quality.py`, skip `~$` temp files, pypdf warning suppression)

### #41 [phase-6] [runtime] Re-index progress + PDF hardening

**Статус:** done (v0.2 — `TMKI_PDF_MAX_PAGES`, heartbeat progress, `reindex_status.py`, `check_ocr_http.py`)

## Phase 2.5 — Делегирование папок (backlog)

### #21 [phase-2] [security] FolderCatalog + EmployeeFolderGrant + delete policy

**Статус:** done (MVP v0.1) — runtime + admin UI + stub SharePoint sync

- `schemas/document/folder-catalog.schema.json`, `employee-folder-grant.schema.json`
- ~~Расширение RLS в `tmki_rag` по `folder_id`~~ ✅
- ~~`tmki_ingest` — resolve `source_path` + gate upload/delete~~ ✅
- ~~UI галочек deny/grant~~ ✅ — `runtime/tmki_admin` (`python -m tmki_admin`)
- ~~Stub SharePoint sync~~ ✅ — `runtime/tmki_sharepoint` (production Graph API — backlog)
