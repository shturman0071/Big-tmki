# TMKI Engineering Handbook v0.2

Статус: APPROVED.

## Назначение

Этот репозиторий — краткий “операционный” хэндбук для инженерной команды TMKI: какие строительные блоки используем, какие принципы считаем обязательными, и как выглядят базовые контракты между слоями (runtime, инструменты, безопасность, обработка документов).

## Как читать

- Если вы внедряете/интегрируете ИИ-фичи — начните с `10_ai_runtime.md`, затем `16_tool_registry.md` и `09_document_processing.md`.
- Если вы проектируете доступы и хранение данных — начните с `07_security_addendum.md` и `ORG_MODEL.md`.
- Если вы выбираете технологии/провайдеров — смотрите `18_technology_watch.md`.

## Структура (оглавление)

- `ORG_MODEL.md` — орг-модель и связи “компания → роли → сотрудники / проекты”.
- `07_security_addendum.md` — обязательные security-требования (RLS, секреты, аудит, rate limits, guardrails).
- `09_document_processing.md` — слой Document Intelligence: OCR → Markdown → метаданные → чанки → эмбеддинги → поиск.
- `10_ai_runtime.md` — TMKI AI Runtime: компоненты, потоки данных, ответственность модулей.
- `13_ai_skills_registry.md` — реестр “скиллов” (повторно используемых паттернов/процедур).
- `16_tool_registry.md` — реестр инструментов и провайдеров, которые допускаются к использованию.
- `18_technology_watch.md` — approved/watchlist и процесс принятия/пересмотра технологий.
- `schemas/runtime/` — JSON Schema контрактов Run, Step, Event, Loop State (v0.1).
- `schemas/document/` — JSON Schema ingest/dedup Document Intelligence (v0.1).
- `schemas/tools/` — Tool Registry, provider pattern, tool call contracts (v0.1).
- `schemas/security/` — MVP security-review checklist (v0.1).

## Конвенции

- **MUST/SHOULD/MAY**: используем RFC-стиль (обязательное/рекомендуемое/опциональное).
- **Provider pattern**: внешние интеграции оформляются как провайдеры со стабильным интерфейсом.
- **Аудитируемость**: существенные действия runtime (tool calls, доступы к данным, выдача ответов) должны оставлять след в аудит-логах.

## Управление изменениями

Владельцы глав, апрув MUST-требований и триггеры security-review: `AGENTS.md` §Владельцы и апрув.

## CI

GitHub CLI: `winget install GitHub.cli` → `gh auth login` → `.\scripts\create-github-issues.ps1`  
GitHub Actions: `.github/workflows/handbook-ci.yml` — markdown lint + secret scan (gitleaks) на каждый push/PR в `main`.

## Roadmap

План работ и backlog задач: `docs/ROADMAP.md`.  
MVP runtime flow: `schemas/runtime/mvp-flow.json`.
