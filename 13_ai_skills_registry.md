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

### Legal Corpus Curator

- **intent**: еженедельное обновление внешней нормативной базы РФ по каталогу.
- **inputs**: `schemas/document/legal-corpus-catalog.json`, доступ к официальным источникам.
- **outputs**: `regulatory-update.schema.json` records, re-indexed chunks, уведомление куратору.
- **constraints**: только лицензированные/официальные URL; audit `regulatory_corpus_updated`.
- **checklist**: fetch → hash diff → ingest → notify → weekly report.
- **owner**: Projektleiter (Design) — Хофманн С.; co-sign Security owner.
- **example**: новая редакция ФЗ 116-ФЗ → diff → ingest → email куратору Промбезопасности.

### Document Author

- **intent**: создание/правка документов по внутренним шаблонам TMKI.
- **inputs**: `document-creation-policy.schema.json`, template_id, черновик.
- **outputs**: docx/pdf в папке сотрудника; audit `document_created`.
- **constraints**: договор — проверка по РФ всегда; прочие — только по запросу (`20_product_requirements_v0_3.md` §5).
- **checklist**: выбрать шаблон → заполнить → internal review → (optional) external law check.
- **owner**: Projektleiter (Design) — Хофманн С.
- **example**: инструкция по крану из шаблона TMKI без auto-check по ГОСТ до запроса инженера.

### Voice Meeting Assistant

- **intent**: голосовые to-do и планёрки с идентификацией спикера.
- **inputs**: `voice-session.schema.json`, voice profile (при consent), аудиопоток.
- **outputs**: transcript, todo items, meeting action items; TTS ответ (Piper `generated_default`).
- **constraints**: speaker ID только при `consent_signed`; HR card не в RAG; TTS — только preset Piper, без клонирования актёра.
- **checklist**: STT → speaker ID → extract actions → store todo → TTS + display cast.
- **owner**: ГИП (runtime) — Дядин С.; co-sign HR.
- **example**: планёрка Сатимол → 3 action items по спикерам → вывод на TV в офисе.

## Cursor: маршрутизация skills (v0.2)

> Правило для агента: `.cursor/rules/skills-routing.mdc`.  
> Паттерн [cursor-skills](https://github.com/chrisboden/cursor-skills) — TMKI-специфичные skills в `.cursor/skills/`, общие процедуры в `runtime/.agents/skills/`.

| Каталог | Назначение | Примеры |
|---------|------------|---------|
| `.cursor/skills/` | Домен TMKI (хэндбук, vsdx) | `tmki-handbook-update`, `vsdx-org-import` |
| `runtime/.agents/skills/` | Инженерные процедуры | `code-review`, `tdd`, `wayfinder`, `domain-modeling` |
| `scripts/` | CLI / PoC (не skill) | `watch_load_skru2.py`, `legal_corpus_curator.py`, `eval_pdf_oxide_poc.py` |

**MUST NOT:** подключать Kit-MCP, gurupdf-mcp, fetch-mcp для данных Сатимол. RAG — только `tmki-rag` MCP.

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
| `20_product_requirements_v0_3.md` | desktop sync, нормативная база, голос |
