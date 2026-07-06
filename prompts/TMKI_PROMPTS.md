# Готовые промпты TMKI BIG

Единый каталог промптов для RAG, анализа документов, генерации Q&A и подготовки LoRA.

## Быстрый старт

| Задача | Файл / команда |
|--------|----------------|
| Системный промпт RAG | `prompts/system_prompt.txt` (`TMKI_SYSTEM_PROMPT_PATH` в `config/rag_config.env`) |
| Расширенный (структура) | `prompts/system_prompt_extended.txt` |
| Каталог всех шаблонов | `prompts/catalog.json` |
| Python API | `runtime/tmki_runtime/prompt_catalog.py` |
| Генерация Q&A | `python runtime/scripts/generate_qa_pairs.py --source ./data/test_docs --output ./data/ground_truth/generated_qa.jsonl` |

## 1. Системные промпты

- **1.1 Базовый** — `prompts/system_prompt.txt` (уже подключён к Ollama/OpenAI через `tmki_llm/providers.py`)
- **1.2 Расширенный** — `prompts/system_prompt_extended.txt` (для analyze / структурного разбора)

Переключение расширенного: `TMKI_SYSTEM_PROMPT_PATH=prompts/system_prompt_extended.txt`

## 2. Анализ структуры

| ID | Файл |
|----|------|
| `analyze_structure` | `prompts/tasks/analyze_structure.txt` |
| `extract_logic` | `prompts/tasks/extract_logic.txt` |

```python
from tmki_runtime.prompt_catalog import render_task_prompt
prompt = render_task_prompt("analyze_structure", context=text)
```

## 3. Генерация Q&A

| ID | Назначение |
|----|------------|
| `qa_generate_basic_system` + `qa_generate_basic_user` | Базовые пары (Azure-style JSON) |
| `qa_generate_typed` | factual / understanding / analysis / application |
| `qa_generate_multihop` | Вопросы из нескольких разделов |

CLI:

```powershell
cd runtime
$env:PYTHONPATH="."
python scripts/generate_qa_pairs.py `
  --source ../data/test_docs `
  --output ../data/ground_truth/generated_qa.jsonl `
  --template qa_generate_typed `
  --limit 5
```

Альтернатива (watchlist): **Docling SDG** — `pip install docling-sdg` (см. `18_technology_watch.md`).

## 4. Форматы документов

| Формат | ID шаблона |
|--------|------------|
| PDF | `format_pdf_analyze` |
| XLSX | `format_xlsx_analyze` |
| DOCX | `format_docx_analyze` |
| DWG/DXF | `format_dwg_analyze` |

Перед подстановкой извлеките текст через `tmki_ocr.extractors.extract_local_text` или `tmki_demo.doc_voice.preview_document_text`.

## 5. Оценка качества

| ID | Критерии |
|----|----------|
| `eval_completeness` | полнота, точность, цитирование, структура (1–5) |
| `eval_structure` | тип документа, разделы, иерархия |

Интеграция с demo: `runtime/tmki_demo/qa_eval.py` + `data/ground_truth/*_qa.json`.

## 6. Тестовый набор

Шаблон: `test_set_create` → JSON с `doc_id`, `questions[]`, `expected_answer`, `difficulty`.

## 7. LoRA-датасет

Шаблон: `lora_dataset_prepare` — из логов RAG (`model-corrections.json`, сессии voice-doc).

## 8. Чек-лист после прогона

1. Прогоните `analyze_structure` на 5–10 документах разных типов
2. Сгенерируйте Q&A → `data/ground_truth/generated_qa.jsonl`
3. Ручная выборочная проверка (убрать галлюцинации)
4. Конвертируйте в suite для `qa_eval` или `tests/test_rag.py`
5. При низком качестве — сначала индекс/reindex, затем LoRA

## Связь с runtime

| Режим LLM | Поведение |
|-----------|-----------|
| `qa` | базовый system_prompt + цитаты |
| `analyze` / `summarize` | структурированный разбор (встроено в providers.py) |
| `voice` | короткий ответ без источников (голосовой стенд) |

Полный список ID: `python -c "from tmki_runtime.prompt_catalog import list_prompts; print(list_prompts())"`
