# AI Skills

## Назначение

“Скиллы” — это повторно используемые инженерные процедуры/паттерны для AI Runtime (и команды), которые описывают **как** выполнять типовые задачи безопасно и воспроизводимо: от разработки harness'ов до ревью безопасности.

Владение скиллами: `AGENTS.md` §Владельцы и апрув.

## Формат записи (SHOULD)

- **name**
- **intent**: какую проблему решает
- **inputs/outputs**: что нужно на вход, что ожидаем на выход
- **constraints**: лимиты, запреты, требования безопасности
- **checklist**: минимальный пошаговый алгоритм
- **owner**: кто поддерживает (роль + ФИО по `ORG_MODEL.md`)
- **example**: один референсный сценарий

## Skills (approved)

### Harness Engineering

- **intent**: воспроизводимый harness для агента (контекст, инструменты, лимиты, трассировка).
- **inputs**: сценарий, policy, tool registry, тестовые кейсы.
- **outputs**: harness config, trace logs, отчёт о прогоне.
- **constraints**: MUST audit, MUST budget limits (см. `10_ai_runtime.md`).
- **checklist**: определить Run → Step → Event; зафиксировать policy_version; прогнать с judge.
- **owner**: ГИП (runtime) — Дядин С. (`ORG_MODEL.md`)
- **example**: MVP Сатимол — Chefmarkscheider запрос → `mvp-flow.json` happy path с `trace_id` и audit chain.

### Looper

- **intent**: многошаговые задачи (план → tool calls → проверка) в Loop Engine.
- **inputs**: goal, ContextBundle, доступные tools.
- **outputs**: step plan, результаты tool calls, финальный verdict.
- **constraints**: circuit breaker, max steps/time/cost (см. `10_ai_runtime.md`).
- **checklist**: план → guardrails на каждом шаге → judge перед выдачей.
- **owner**: ГИП (runtime) — Дядин С.
- **example**: RAG → `llm_openai` → повторный `rag_search` при `judge_fail` (max 1 retry) — см. `10_ai_runtime.md` degraded paths.

### Ponytail

- **intent**: структурирование длинного контекста / “хвоста” диалога и памяти.
- **inputs**: история, Memory Tree, лимиты токенов.
- **outputs**: сжатый ContextBundle с приоритетами.
- **constraints**: не терять цитируемые источники; маскировать PII (см. `07_security_addendum.md`).
- **checklist**: выделить факты vs гипотезы → применить TTL → проверить размер bundle.
- **owner**: ГИП (runtime) — Дядин С.
- **example**: длинная переписка по проекту Сатимол → сжатие до budget `max_tokens`, citations из RAG сохранены в bundle.

### make-interfaces-feel-better

- **intent**: улучшение UX взаимодействия с агентом (ясность, обратная связь, деградации).
- **inputs**: user flows, типовые ошибки runtime.
- **outputs**: UX-рекомендации, тексты деградации (read-only, low confidence).
- **constraints**: не скрывать uncertainty; явные ссылки на источники (RAG).
- **checklist**: сценарии ошибок из `10_ai_runtime.md` → тексты → review.
- **owner**: Projektleiter (Design) — Хофманн С.
- **example**: `guardrail_block` → пользователю текст «ответ заблокирован политикой» + `error_code`, без сырого LLM output.

### Security Review

- **intent**: проверка изменений перед релизом (RLS, секреты, guardrails, audit).
- **inputs**: diff/PR, затронутые модули, threat model.
- **outputs**: чеклист pass/fail, список блокеров.
- **constraints**: MUST сверка с `07_security_addendum.md` и `ORG_MODEL.md`.
- **checklist**: полный MVP checklist — `schemas/security/mvp-security-review.checklist.json`; краткий: RLS → secrets → tool gating → rate limits → guardrails PII.
- **owner**: Владелец ИБ — разработчик [@shturman0071](https://github.com/shturman0071); co-sign: Projektleiter — Нефф А.
- **example**: PR с изменением `tool-gating.rules.json` → прогон checks TL и SEC из checklist → sign-off в `mvp-security-review.schema.json`.

## Связь с runtime

- **Loop Engine** использует “Looper”-подобные процедуры для многошаговых задач.
- **Judge/Guardrails** опираются на “Security Review”-подобные чеклисты для контроля риска.
- **Context Builder** может использовать “Ponytail” для сжатия контекста.

## Связанные документы

| Документ | Связь |
|----------|-------|
| `AGENTS.md` | владельцы скиллов, апрув |
| `10_ai_runtime.md` | Loop Engine, Judge, Guardrails, Audit |
| `07_security_addendum.md` | Security Review, MVP security-review checklist |
| `16_tool_registry.md` | инструменты в harness |
| `18_technology_watch.md` | Harness Engineering Guide (approved) |
