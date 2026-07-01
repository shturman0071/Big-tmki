# AGENTS.md — TMKI Engineering Handbook / Big-tmki

## Что это за проект

Операционный инженерный хэндбук TMKI v0.2: runtime, безопасность, обработка документов, реестры инструментов и скиллов, оргмодель.

- **Репозиторий:** <https://github.com/shturman0071/Big-tmki>
- **Ветка по умолчанию:** `main`
- **Статус хэндбука:** УТВЕРЖДЁН (см. `README.md`)
- **Процесс изменений:** см. раздел «Владельцы и апрув» ниже

## С чего начинать

1. Прочитать `README.md` (оглавление и конвенции).
2. Для задачи открыть связанные главы (см. «Карта глав» ниже).
3. Сверить изменения с `.cursor/rules/` и при необходимости применить skills из `.cursor/skills/`.

## Карта глав

| Файл | Тема |
|------|------|
| `ORG_MODEL.md` | Оргструктура, роли, RLS-маппинг, `schemas/org/` |
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

Локальный архив регламентов: `d:\Курсор\ТМКИ оригнал\` (~1200+ файлов, не коммитить). Импорт — по `docs/ROADMAP.md` #6.

## Владельцы и апрув (v0.1)

> Roadmap #2. Роли привязаны к `ORG_MODEL.md` (проект «Сатимол»). ФИО — по оргсхеме 10.09.2025; при смене роли обновлять эту таблицу.

### Матрица владения

| Область | Файлы / артефакты | Owner (роль) | Назначенный (по схеме) |
|---------|-------------------|--------------|------------------------|
| Хэндбук (custodian) | `README.md`, `AGENTS.md`, `docs/ROADMAP.md` | Projektleiter (РП) | Нефф А. |
| Security baseline | `07_security_addendum.md`, `schemas/security/` | Служба ОТ и ПБ + РП | TBD (ИБ) |
| Org / RLS | `ORG_MODEL.md` | Projektleiter + ГИП | Нефф А., Дядин С. / Гаер Д. |
| AI Runtime | `10_ai_runtime.md`, `schemas/runtime/` | ГИП (runtime) | Дядин С. |
| Document Intelligence | `09_document_processing.md`, `schemas/document/` | Projektleiter (Design) | Хофманн С. |
| Tool Registry | `16_tool_registry.md`, `schemas/tools/` | ГИП + Projektleiter (Design) | Дядин С. |
| Skills | `13_ai_skills_registry.md` | ГИП (runtime) | Дядин С. |
| Technology Watch | `18_technology_watch.md` | Projektleiter + ГИП | Нефф А. |

### Апрув изменений MUST (MUST)

1. Изменения — через PR в `main`; CI (`handbook-ci.yml`) MUST проходить.
2. Правка MUST-требований в главе owner'а — **апрув owner'а** (комментарий или review в PR).
3. Правка MUST в `07_security_addendum.md`, `ORG_MODEL.md` (RLS), `schemas/security/`, `tool-gating.rules.json` — **апрув Security owner** + custodian (РП).
4. Правка `schemas/runtime/`, `mvp-flow.json`, Loop/Judge — **апрув ГИП (runtime)** + при затрагивании security — Security owner.
5. Статус `УТВЕРЖДЁН` в `README.md` не менять без явного решения custodian (РП).

### Когда обязателен security-review (MUST)

| Триггер | Действие |
|---------|----------|
| Первый MVP / production deploy runtime | Полный checklist: `schemas/security/mvp-security-review.checklist.json` |
| Новый write-tool (`T_w`) или изменение `tool-gating.rules.json` | Security Review skill + owner sign-off |
| Изменение RLS-матрицы, `classification`, clearance | Security owner + сверка с `ORG_MODEL.md` |
| Новая Approved-технология с network/data access | Процесс `18_technology_watch.md` п.3 + security-review |
| Инцидент / утечка / обход guardrails | Внеплановый review; blockers до устранения |

Детали: `07_security_addendum.md` §MVP Security Review, skill Security Review в `13_ai_skills_registry.md`.

### Когда обновлять `README.md` (SHOULD)

- добавлена или переименована глава в корне репозитория;
- добавлен каталог в `schemas/` (новый домен контрактов);
- изменён «Как читать» или порядок онбординга;
- изменён статус хэндбука (`APPROVED` / draft).

Структурные правки без смены оглавления — README MAY не трогать.

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

## Непрерывная интеграция

Workflow `.github/workflows/handbook-ci.yml`: проверка markdown + gitleaks на push/PR в `main`.

## Skills проекта

| Skill | Когда использовать |
|-------|-------------------|
| `tmki-handbook-update` | Дополнение/синхронизация глав хэндбука |
| `vsdx-org-import` | Импорт оргструктуры из Visio `.vsdx` |

## План работ

План работ и backlog: `docs/ROADMAP.md`.  
Создание issues на GitHub: `scripts/create-github-issues.ps1` (нужен `gh` CLI).
