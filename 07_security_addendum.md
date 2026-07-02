# Security

## Базовый стандарт

- **OWASP**: ориентируемся на OWASP ASVS (уровень уточняется в зависимости от продукта), плюс OWASP Top 10 как минимальный чеклист.

## Доступ к данным (MUST)

- **RLS mandatory**: строковая безопасность (Row Level Security) обязательна для многопользовательских таблиц, где возможны пересечения арендаторов/проектов.
- **Server-side authorization**: решения “можно/нельзя” принимаются только на сервере.
- **Принцип наименьших привилегий**: сервисы/инструменты получают минимум прав под конкретную задачу.
- **position_id**: должность сотрудника (Position), используется для определения `is_manager`.
- **is_manager**: флаг, вычисляемый из Position; определяет право выдавать grant/deny на папки (`EmployeeFolderGrant`).

## Валидация и доверие к вводу (MUST)

- **Server-side validation**: входные данные валидируются на сервере (схемы, типы, диапазоны).
- **Никакого доверия к LLM output**: результат модели — это непроверенный ввод; перед tool calls/записью в БД требуется валидация.

## Секреты (MUST)

- **Secrets Policy**:
  - секреты не коммитятся в репозиторий
  - секреты не логируются в открытом виде
  - секреты не отправляются в LLM-контекст (кроме строго необходимого и только через безопасные каналы)
- **Ротация**: ключи и токены должны быть ротируемыми; инциденты требуют принудительной ротации.

## Rate limiting и защита от злоупотреблений (MUST)

- **Rate limiting**: лимиты на пользователя/организацию/IP, отдельные лимиты на tool calls и OCR/индексацию.
- **Budgeting**: лимиты стоимости/токенов на Run/сессию (см. `10_ai_runtime.md`, сущности Run/Step).
- **Circuit breaker**: остановка при повторяющихся ошибках или подозрительной активности.

## Security headers (SHOULD)

- базовый набор заголовков безопасности для веб-приложения (CSP, HSTS, X-Content-Type-Options и т. п.) в зависимости от архитектуры

## Audit logs (MUST)

- **Audit logs**:
  - фиксировать: аутентификацию, изменения доступов/ролей, доступ к документам, tool calls, изменение конфигураций guardrails
  - связывать события через `trace_id` / `run_id` (см. `10_ai_runtime.md`, Event; каталог: `schemas/runtime/audit-event-catalog.json`)
  - хранить payload в санитизированном виде (без секретов/лишних PII)

## AI Guardrails (MUST)

- **Политики**: запреты/ограничения на действия (например, “не выполнять write-операции без явного подтверждения пользователя”, если применимо).
- **PII & Secrets**: детект/редакция/блокирование.
- **Tool gating**: запуск инструмента только если удовлетворены условия policy (роль, окружение, тип запроса, риск).
- **Model governance**: список разрешенных моделей/провайдеров и правила переключения (см. `18_technology_watch.md`, `16_tool_registry.md`).

## Минимальный security-review перед релизом (SHOULD)

- проверка RLS/ACL
- проверка логирования (нет секретов)
- проверка лимитов и бюджетов
- проверка критичных guardrails (PII, запрещенные действия)

## MVP Security Review (v0.1)

> **Phase 6 #19** — обязателен перед первым MVP-релизом runtime.  
> Skill: `13_ai_skills_registry.md` → Security Review.

### Артефакты

| Файл | Назначение |
|------|------------|
| `schemas/security/mvp-security-review.checklist.json` | 28 проверок в 9 категориях |
| `schemas/security/mvp-security-review.schema.json` | Формат результата review |
| `schemas/security/examples/mvp-security-review.example.json` | Пример sign-off |

### Процедура (MUST)

1. Назначить reviewer (ИБ / security owner).
2. Пройти все пункты с `must_pass: true` в checklist.
3. Зафиксировать результат в `mvp-security-review.schema.json` (pass / pass_with_notes / fail).
4. При `fail` — blockers MUST быть устранены до релиза.
5. При `pass_with_notes` — deferred items MUST иметь owner и срок.

### Категории checklist

| Категория | ID prefix | Фокус |
|-----------|-----------|-------|
| RLS и доступы | ACC-* | server-side filter, policy_context, clearance |
| Tool gating | TL-* | checkPolicy, watchlist, T_w excluded |
| Секреты | SEC-* | repo, registry, audit, LLM secret_scan |
| Audit | AUD-* | trace_id, MVP events, document_accessed |
| Guardrails / Judge | GRD-* | block, redact, judge before completed |
| Limits | LIM-* | budget, circuit breaker, rate limits |
| Documents | DOC-* | ingest dedup, clearance, OCR fallback |
| Governance | GOV-* | approved providers, policy_version |
| MVP cross-check | MVP-* | mvp-flow acceptance criteria |

### Правила sign-off

| `overall_status` | Условие |
|------------------|---------|
| `pass` | все `must_pass=true` → pass |
| `pass_with_notes` | все must pass; optional items deferred с owner |
| `fail` | любой `must_pass=true` → fail |

### Связь с Judge

Judge в runtime **SHOULD** использовать подмножество GRD-* checks на каждом Run; полный checklist — при релизе/изменении policy.

## Связанные документы

| Документ | Связь |
|----------|-------|
| `10_ai_runtime.md` | Guardrails, Audit, Run/Step budget, JSON schemas |
| `ORG_MODEL.md` | RLS-поля (`company_id`, `project_id`, `department_id`, `project_role`), матрица ролей |
| `09_document_processing.md` | фильтрация доступа к документам до выдачи |
| `16_tool_registry.md` | tool gating, policy hooks |
| `18_technology_watch.md` | model governance, approved-провайдеры |
| `schemas/security/` | MVP security-review checklist и sign-off |
