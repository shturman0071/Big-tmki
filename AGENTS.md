# AGENTS.md — TMKI Engineering Handbook / Big-tmki

## Что это за проект

Операционный инженерный хэндбук TMKI v0.2: runtime, безопасность, обработка документов, реестры инструментов и скиллов, оргмодель.

- **Репозиторий:** <https://github.com/shturman0071/Big-tmki>
- **Ветка по умолчанию:** `main`
- **Статус хэндбука:** APPROVED (см. `README.md`)

## С чего начинать

1. Прочитать `README.md` (оглавление и конвенции).
2. Для задачи открыть связанные главы (см. «Карта глав» ниже).
3. Сверить изменения с `.cursor/rules/` и при необходимости применить skills из `.cursor/skills/`.

## Карта глав

| Файл | Тема |
|------|------|
| `ORG_MODEL.md` | Оргструктура, роли, RLS-маппинг |
| `07_security_addendum.md` | Security baseline |
| `09_document_processing.md` | Document Intelligence pipeline |
| `10_ai_runtime.md` | AI Runtime, контракты Run/Step/Event |
| `13_ai_skills_registry.md` | Реестр инженерных скиллов |
| `16_tool_registry.md` | Реестр инструментов и провайдеров |
| `18_technology_watch.md` | Approved / Watchlist технологий |

## Исходники вне репозитория

Оригиналы (Visio, чертежи и т. п.) лежат локально, **не коммитятся**:

- `d:\Курсор\ТМКИ оригнал\` — в т. ч. `Орг Структура Сатимола_проект_10092025.vsdx`

При импорте из `.vsdx` обновлять `ORG_MODEL.md` и указывать источник/дату схемы.

## Правила работы агента

- Язык ответов и документации: **русский**.
- Стиль требований: **MUST / SHOULD / MAY** (RFC).
- **Не создавать** новые `.md` без явного запроса пользователя.
- **Не коммитить и не пушить** без явного запроса.
- **Не коммитить:** секреты, `.env`, токены, большие бинарники (`.vsdx`), временные `_vsdx_*`.
- Минимальный scope: менять только то, что нужно для задачи.
- При правке главы проверять перекрёстные ссылки с связанными файлами.

## Git

```text
origin  https://github.com/shturman0071/Big-tmki.git
branch  main
```

Формат коммита: краткий заголовок + 1–2 предложения «зачем».

## CI

Workflow `.github/workflows/handbook-ci.yml`: markdownlint + gitleaks на push/PR в `main`.

## Skills проекта

| Skill | Когда использовать |
|-------|-------------------|
| `tmki-handbook-update` | Дополнение/синхронизация глав хэндбука |
| `vsdx-org-import` | Импорт оргструктуры из Visio `.vsdx` |

## Roadmap

План работ и backlog: `docs/ROADMAP.md`.  
Создание issues на GitHub: `scripts/create-github-issues.ps1` (нужен `gh` CLI).
