# ============================================================
# TMKI Engineering Handbook - Makefile
# ============================================================

.PHONY: help setup test reindex embed rerank clean install

help:
	@echo "Доступные команды:"
	@echo "  make setup      - Установить все зависимости и подготовить окружение"
	@echo "  make test       - Запустить тесты RAG"
	@echo "  make reindex    - Переиндексировать все документы"
	@echo "  make embed      - Обновить эмбеддинги в БД"
	@echo "  make rerank     - Настроить cross-encoder rerank"
	@echo "  make clean      - Очистить временные файлы"
	@echo "  make install    - Установить Python зависимости"

setup: install
	@echo "🚀 Настройка окружения..."
	@echo "1. Проверка Ollama..."
	@ollama pull nomic-embed-text || echo "⚠️ Установите Ollama: https://ollama.ai"
	@ollama pull qwen2.5:7b || echo "⚠️ Установите Ollama: https://ollama.ai"
	@echo "2. Проверка конфига..."
	@test -f config/rag_config.env || cp config/rag_config.env.example config/rag_config.env
	@echo "3. Создание папок..."
	@mkdir -p data/test_docs data/ground_truth logs
	@echo "✅ Настройка завершена!"

install:
	@echo "📦 Установка Python зависимостей..."
	pip install -r requirements.txt || pip install torch sentence-transformers psycopg2-binary docling pypdfium2 tqdm requests pytest python-dotenv pyyaml

test:
	@echo "🧪 Запуск тестов..."
	python -m pytest tests/test_rag.py -v --tb=short || echo "⚠️ Установите pytest: pip install pytest"

reindex:
	@echo "🔄 Переиндексация документов..."
	python scripts/reindex_all.py

embed:
	@echo "📊 Обновление эмбеддингов..."
	python scripts/embedding_update.py

rerank:
	@echo "⚡ Настройка cross-encoder rerank..."
	python scripts/rerank_setup.py

clean:
	@echo "🧹 Очистка..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.log" -delete 2>/dev/null || true
	rm -rf .pytest_cache 2>/dev/null || true
	@echo "✅ Очистка завершена"

demo:
	@echo "🚀 Запуск демо-сервера..."
	python -m runtime.tmki_demo --host 0.0.0.0 --port 8767 || echo "⚠️ Убедитесь, что runtime/tmki_demo существует"

all: setup test
	@echo "✅ Все готово!"
