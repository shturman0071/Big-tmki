# TMKI Engineering Handbook v0.2

Статус: **УТВЕРЖДЁН**.

## Назначение

Этот репозиторий — краткий “операционный” хэндбук для инженерной команды TMKI: какие строительные блоки используем, какие принципы считаем обязательными, и как выглядят базовые контракты между слоями (runtime, инструменты, безопасность, обработка документов).

## Как читать

- Если вы внедряете/интегрируете ИИ-фичи — начните с `10_ai_runtime.md`, затем `16_tool_registry.md` и `09_document_processing.md`.
- Если вы проектируете доступы и хранение данных — начните с `07_security_addendum.md` и `ORG_MODEL.md`.
- Если вы выбираете технологии/провайдеров — смотрите `18_technology_watch.md`.

## Структура (оглавление)

- `ORG_MODEL.md` — орг-модель и связи “компания → роли → сотрудники / проекты”.
- `07_security_addendum.md` — обязательные требования безопасности (RLS, секреты, аудит, лимиты, guardrails).
- `09_document_processing.md` — Document Intelligence: OCR → Markdown → метаданные → чанки → эмбеддинги → поиск.
- `10_ai_runtime.md` — AI Runtime TMKI: компоненты, потоки данных, ответственность модулей.
- `13_ai_skills_registry.md` — реестр инженерных скиллов (повторно используемые процедуры).
- `16_tool_registry.md` — реестр инструментов и провайдеров.
- `18_technology_watch.md` — утверждённые технологии / watchlist и процесс пересмотра.
- `20_product_requirements_v0_3.md` — требования v0.3: рабочий стол, sync, нормативная база, голос (DRAFT).
- `schemas/runtime/` — JSON Schema контрактов Run, Step, Event, Loop State (v0.1).
- `schemas/document/` — JSON Schema ingest/dedup Document Intelligence (v0.1).
- `schemas/tools/` — реестр инструментов, provider pattern, контракты вызовов (v0.1).
- `schemas/security/` — чеклист security-review перед MVP (v0.1).
- `schemas/org/` — сущности оргмодели: компания, подразделение, должность, сотрудник, проект, назначение (v0.1).
- `runtime/` — код MVP runtime: `tmki_policy`, `tmki_rag`, `tmki_tools`, `tmki_loop`, `run_mvp`.

## Конвенции

- **MUST/SHOULD/MAY**: используем RFC-стиль (обязательное/рекомендуемое/опциональное).
- **Паттерн провайдеров**: внешние интеграции оформляются как провайдеры со стабильным интерфейсом.
- **Аудитируемость**: существенные действия runtime (вызовы инструментов, доступы к данным, выдача ответов) должны оставлять след в журнале аудита.

## Управление изменениями

Владельцы глав, апрув MUST-требований и триггеры security-review: `AGENTS.md` §Владельцы и апрув.

## Непрерывная интеграция

GitHub CLI: `winget install GitHub.cli` → `gh auth login` → `.\scripts\create-github-issues.ps1`  
GitHub Actions: `.github/workflows/handbook-ci.yml` — проверка markdown и сканирование секретов (gitleaks) на каждый push/PR в `main`.

## План работ

План работ и backlog задач: `docs/ROADMAP.md`.  
MVP-сценарий runtime: `schemas/runtime/mvp-flow.json`.
