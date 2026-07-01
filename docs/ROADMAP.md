# Roadmap — Big-tmki / TMKI Engineering Handbook

План работ по фазам. Каждый пункт ниже — кандидат в GitHub Issue.

**Репозиторий:** https://github.com/shturman0071/Big-tmki

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

- Кто апрувит изменения MUST-требований
- Когда обязателен security-review
- Когда обновлять `README.md`

---

### #3 [phase-0] Установить GitHub CLI и завести labels

```powershell
winget install GitHub.cli
gh auth login
gh label create phase-0 phase-1 phase-2 phase-3 phase-4 phase-5 phase-6 security runtime docs --repo shturman0071/Big-tmki
```

Затем: `.\scripts\create-github-issues.ps1`

---

## Phase 1 — Документация

### #4 [phase-1] [docs] Дописать `13_ai_skills_registry.md` — owners

- Назначить owner для каждого skill
- Добавить примеры inputs/outputs (1 сценарий на skill)

---

### #5 [phase-1] [docs] Детализировать `18_technology_watch.md` — карточки Approved

Для каждой Approved-технологии: версия, owner, риски, дата пересмотра, ссылка на `16_tool_registry.md`.

---

### #6 [phase-1] [docs] Импорт регламентов из `ТМКИ оригнал`

- Инвентаризация файлов в `d:\Курсор\ТМКИ оригнал\`
- Выжимка в markdown (без коммита бинарников)
- Skill: `vsdx-org-import` для оргсхем

---

## Phase 2 — Доступы

### #7 [phase-2] [security] Матрица «роль → права → RLS»

**Статус:** done (DRAFT v0.1 в `ORG_MODEL.md`)

На базе `ORG_MODEL.md` (проект Сатимол). Выход: таблица role × resource × action × RLS-поля.

**Осталось:** согласовать открытые вопросы (access_label, подрядчики, group_admin).

---

### #8 [phase-2] [security] Схема сущностей org model

`company`, `department`, `position`, `employee`, `project`, `project_role`, `assignment`.

---

### #9 [phase-2] [docs] Актуализировать вакансии оргсхемы (10.09.2025)

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

pgvector + RLS-поля до выдачи в RAG.

---

## Phase 5–6 — Интеграция (backlog)

### #16 [phase-5] [runtime] Каркас Tool Registry + provider pattern

### #17 [phase-5] [security] Tool gating по org/role/env

### #18 [phase-6] [runtime] MVP: Context → RAG → Loop → Judge → Audit

### #19 [phase-6] [security] Security-review перед MVP-релизом

### #20 [phase-0] CI: markdown lint + secret scan

---

## Текущий фокус (эта неделя)

1. ~~#1 Синхронизация ссылок~~ ✅
2. ~~#7 Матрица роль → права → RLS~~ ✅ (DRAFT v0.1)
3. ~~#10 JSON-схемы Run/Step/Event~~ ✅ (v0.1)
4. ~~#11 State machine Loop Engine~~ ✅ (v0.1)
5. ~~#12 Каталог audit events~~ ✅ (v0.1)
6. ~~#13 Ingest + dedup (Document Intelligence)~~ ✅ (v0.1)
7. ~~#14 OCR pipeline MinerU + fallback~~ ✅ (v0.1)
8. **#15 Индексация с server-side фильтрацией**
9. **#3 Установить gh + создать issues на GitHub**
