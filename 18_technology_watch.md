# Technology Watch

Владение реестром: Projektleiter (Нефф А.) + ГИП (Дядин С.) — см. `AGENTS.md`.

## Approved (карточки v0.1)

| Технология | Версия / pin | Owner | Риски | Пересмотр | Tool Registry |
|------------|--------------|-------|-------|-----------|---------------|
| MinerU | 2.1.0 (`ocr_mineru`) | Projektleiter (Design) — Хофманн С. | качество OCR, внешний API, misclassification | 2026-09-01 | `16_tool_registry.md`, `ocr_mineru` |
| Mistral OCR 4 | 2026-06 (`ocr_mistral`) | Projektleiter (Design) — Хофманн С. | fallback cost, latency, data residency | 2026-09-01 | `ocr_mistral` |
| RAG | pgvector + schemas v0.1 | ГИП — Дядин С. | RLS bypass, stale index, citation drift | 2026-09-01 | `rag_search` |
| Provider Pattern | handbook v0.1 | ГИП — Дядин С. | provider sprawl, inconsistent audit | 2026-09-01 | `16_tool_registry.md` §Provider Pattern |
| Firecrawl | per registry | Projektleiter (Design) — Хофманн С. | web scrape scope, robots/ToS, PII in pages | 2026-09-01 | `firecrawl_scrape` |
| SearXNG | self-hosted TBD | ГИП — Дядин С. | open proxy abuse, result poisoning | 2026-09-01 | watch — not in MVP registry |
| Harness Engineering Guide | methodology | ГИП — Дядин С. | harness drift без version pin | 2026-09-01 | `13_ai_skills_registry.md` |
| Super Context | pattern TBD | ГИП — Дядин С. | context overflow, lost citations | 2026-09-01 | — |
| Ponytail | pattern | ГИП — Дядин С. | over-compression, PII in summary | 2026-09-01 | skill в `13_ai_skills_registry.md` |
| make-interfaces-feel-better | pattern | Projektleiter (Design) — Хофманн С. | скрытие uncertainty | 2026-09-01 | skill в `13_ai_skills_registry.md` |
| OWASP | ASVS (уровень TBD) | Security owner — TBD | compliance gap vs product | 2026-12-01 | `07_security_addendum.md` |
| RLS | Postgres RLS + ORG_MODEL | Security owner + РП | policy drift, contractor scope | 2026-09-01 | `ORG_MODEL.md` |

## Критерии “Approved” (SHOULD)

- **Безопасность**: понятная модель угроз, поддержка изоляции арендаторов/доступов, отсутствие критичных уязвимостей.
- **Наблюдаемость**: метрики/логи/трейсы, достаточные для эксплуатации.
- **Стабильность**: понятная политика версий, прогнозируемые breaking changes.
- **Экономика**: измеряемая стоимость (latency/цена), возможность бюджетирования.
- **Совместимость**: легко “вписывается” в provider pattern и контракты runtime.

## Процесс добавления технологии

1) **Краткая записка**: что это, где применяем, какие альтернативы.
2) **PoC**: минимальная интеграция + измерения (latency, качество, цена).
3) **Security review**: оценка рисков (данные, доступы, side-effects).
4) **Операционный план**: мониторинг, лимиты, деградации, план отката.
5) **Решение**: пометка в `Approved` или `Watchlist`; обновить карточку в таблице выше.

## Периодический пересмотр (SHOULD)

- ежеквартально пересматривать `Watchlist` и даты в карточках Approved
- при инциденте/уязвимости — внеплановый пересмотр и возможный “демоут” из `Approved`

## Watchlist

| Технология | Причина watch | Owner | Пересмотр |
|------------|---------------|-------|-----------|
| zvec | альтернатива vector stack, не валидирован | ГИП — Дядин С. | 2026-09-01 |
| Camofox | browser automation risk, production blocked | Security owner — TBD | 2026-07-15 |
| Gemma 4 12B | local model governance | ГИП — Дядин С. | 2026-09-01 |
| Local LLM Optimization | ops complexity, no MVP path | ГИП — Дядин С. | 2026-09-01 |

## Связанные документы

| Документ | Связь |
|----------|-------|
| `AGENTS.md` | владельцы, апрув Approved |
| `16_tool_registry.md` | конкретные инструменты по категориям |
| `10_ai_runtime.md` | provider pattern, model governance в runtime |
| `07_security_addendum.md` | security review при добавлении технологии |
| `09_document_processing.md` | MinerU, Mistral OCR 4, vector stack |
| `schemas/tools/providers.registry.json` | версии и policy tools |
