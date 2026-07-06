# ============================================================
# TMKI Engineering Handbook - Makefile
# ============================================================

.PHONY: help setup test check-demo reindex embed rerank clean install demo all legacy-test legacy-reindex watch-skru2

help:
	@echo "Доступные команды:"
	@echo "  make setup      - Установить зависимости и подготовить окружение"
	@echo "  make test       - Тесты RAG (корень)"
	@echo "  make load-skru2      - Загрузить 5000 чанков СКРУ-2 в PG (Ollama 768)"
	@echo "  make load-skru2-resume - Продолжить загрузку СКРУ-2"
	@echo "  make watch-skru2  - Мониторинг загрузки СКРУ-2 в реальном времени"
	@echo "  make reindex    - Переиндексация data/test_docs -> PostgreSQL chunks"
	@echo "  make embed      - Обновить эмбеддинги в БД"
	@echo "  make rerank     - Настроить cross-encoder rerank"
	@echo "  make demo       - Запуск demo UI (start-demo.ps1 / :8770)"
	@echo "  make legacy-test    - pytest runtime/"
	@echo "  make legacy-reindex - runtime reindex СКРУ-2"

setup: install
	@echo "Настройка окружения..."
	@ollama pull nomic-embed-text || echo "Установите Ollama: https://ollama.ai"
	@ollama pull qwen2.5:7b || echo "Установите Ollama: https://ollama.ai"
	@test -f config/rag_config.env || cp config/rag_config.env.example config/rag_config.env
	@mkdir -p data/test_docs data/ground_truth logs
	@echo "Готово."

install:
	pip install -r requirements.txt || pip install -e runtime/.[ocr,search,rerank,ingest-docling,stt]

test:
	python -m pytest tests/test_rag.py -v --tb=short

check-demo:
	python scripts/check_demo.py --auto

load-skru2:
	python scripts/load_skru2_to_chunks.py --limit 5000 --replace-corpus

load-skru2-resume:
	python scripts/load_skru2_to_chunks.py --resume --embed-batch 48 --batch 400

load-skru2-fast:
	python scripts/load_skru2_to_chunks.py --resume --embed-batch 64 --batch 400

watch-skru2:
	python scripts/watch_load_skru2.py --interval 5

watch-ops:
	python scripts/watch_tmki_ops.py --interval 3

ops-run:
	python scripts/ops_runner.py

stop-demo:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/stop_demo.ps1

pto-ui:
	powershell -NoProfile -ExecutionPolicy Bypass -File start-pto-ui.ps1

director-ui:
	powershell -NoProfile -ExecutionPolicy Bypass -File start-director-ui.ps1

eval-pdf-oxide:
	python scripts/eval_pdf_oxide_poc.py --limit 20 --save runtime/artifacts/eval/pdf-oxide-poc.json

legal-corpus-dry-run:
	python scripts/legal_corpus_curator.py --dry-run

legal-corpus-fetch:
	python scripts/legal_corpus_curator.py --fetch --limit 3

setup-pandoc-mcp:
	powershell -NoProfile -ExecutionPolicy Bypass -File runtime/scripts/setup_pandoc_mcp.ps1

legacy-test:
	cd runtime && python -m pytest -q

legacy-reindex:
	cd runtime && powershell -NoProfile -ExecutionPolicy Bypass -File scripts/rebuild_regulations_index.ps1 -Resume

reindex:
	python scripts/reindex_all.py

embed:
	python scripts/embedding_update.py

rerank:
	python scripts/rerank_setup.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache runtime/.pytest_cache 2>/dev/null || true

demo:
	powershell -NoProfile -ExecutionPolicy Bypass -File start-demo.ps1

all: setup test
