# Technology Watch

## Approved
- MinerU
- Mistral OCR 4
- Harness Engineering Guide
- Super Context
- make-interfaces-feel-better
- Ponytail
- SearXNG
- Firecrawl
- RAG
- Provider Pattern
- OWASP
- RLS

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
5) **Решение**: пометка в `Approved` или `Watchlist`.

## Периодический пересмотр (SHOULD)

- ежеквартально пересматривать `Watchlist`
- при инциденте/уязвимости — внеплановый пересмотр и возможный “демоут” из `Approved`

## Watchlist
- zvec
- Camofox
- Gemma 4 12B
- Local LLM Optimization

## Связанные документы

| Документ | Связь |
|----------|-------|
| `16_tool_registry.md` | конкретные инструменты по категориям |
| `10_ai_runtime.md` | provider pattern, model governance в runtime |
| `07_security_addendum.md` | security review при добавлении технологии |
| `09_document_processing.md` | MinerU, Mistral OCR 4, vector stack |
