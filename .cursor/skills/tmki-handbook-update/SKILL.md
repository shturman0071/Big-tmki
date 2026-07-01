---
name: tmki-handbook-update
description: Updates and synchronizes TMKI Engineering Handbook chapters (runtime, security, document pipeline, registries). Use when editing handbook .md files, expanding chapters, or keeping cross-references consistent across README, ORG_MODEL, and numbered chapters.
---

# TMKI Handbook Update

## Перед правками

1. Прочитать `README.md` и целевую главу.
2. Определить связанные главы (см. таблицу ниже).
3. Применить `.cursor/rules/handbook-style.mdc`.

## Карта зависимостей

| Если меняете | Проверить |
|--------------|-----------|
| `10_ai_runtime.md` | `16_tool_registry.md`, `09_document_processing.md`, `07_security_addendum.md` |
| `09_document_processing.md` | `16_tool_registry.md`, `18_technology_watch.md` |
| `16_tool_registry.md` | `18_technology_watch.md`, `10_ai_runtime.md` |
| `18_technology_watch.md` | `16_tool_registry.md` |
| `ORG_MODEL.md` | `07_security_addendum.md`, `README.md`, `AGENTS.md` |
| `07_security_addendum.md` | `10_ai_runtime.md`, `ORG_MODEL.md`, `AGENTS.md` |
| `13_ai_skills_registry.md` | `AGENTS.md` |
| `18_technology_watch.md` | `16_tool_registry.md`, `AGENTS.md` |

## Алгоритм дополнения главы

1. Добавить/уточнить разделы: цель → принципы → контракты/компоненты → связи.
2. Использовать MUST/SHOULD/MAY.
3. Добавить перекрёстные ссылки на другие файлы (без дублирования больших блоков).
4. Если изменилась структура — обновить оглавление в `README.md`.
5. Сверить с `AGENTS.md` §Владельцы и апрув (owner, security-review).
6. Не создавать новые `.md` без запроса пользователя.

## Чеклист перед завершением

- [ ] Терминология согласована с другими главами
- [ ] Security-требования не противоречат `07_security_addendum.md`
- [ ] Инструменты/технологии согласованы с реестрами
- [ ] README актуален (если менялась структура)

## Коммит

Только по явному запросу. Сообщение: что изменено и зачем (1–2 предложения).
