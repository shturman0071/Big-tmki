import os
import sys
import json
import pytest
from typing import List, Dict, Any

# Добавляем путь к проекту
ROOT = os.path.dirname(os.path.dirname(__file__))
RUNTIME = os.path.join(ROOT, "runtime")
sys.path.insert(0, ROOT)
sys.path.insert(0, RUNTIME)

from tmki_runtime.rag_env import load_rag_config
load_rag_config(override=False)

def load_test_data():
    """Загрузить тестовые вопросы-ответы"""
    qa_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ground_truth", "qa_pairs.json")
    if not os.path.exists(qa_path):
        pytest.skip(f"Файл {qa_path} не найден. Создайте тестовые данные.")
    
    with open(qa_path, encoding="utf-8") as f:
        return json.load(f)

def load_expected_citations():
    """Загрузить ожидаемый формат цитирования"""
    citations_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "expected_citations.json")
    if not os.path.exists(citations_path):
        pytest.skip(f"Файл {citations_path} не найден")
    
    with open(citations_path, encoding="utf-8") as f:
        return json.load(f)

def load_system_prompt():
    """Загрузить системный промпт"""
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "system_prompt.txt")
    if not os.path.exists(prompt_path):
        pytest.skip(f"Файл {prompt_path} не найден")
    
    with open(prompt_path, encoding="utf-8") as f:
        return f.read()

class TestRAGQuality:
    """Тесты качества RAG системы"""
    
    @pytest.fixture
    def test_data(self):
        return load_test_data()
    
    @pytest.fixture
    def citations_schema(self):
        return load_expected_citations()
    
    @pytest.fixture
    def system_prompt(self):
        return load_system_prompt()
    
    def test_system_prompt_exists(self, system_prompt):
        """Проверка: системный промпт существует и не пуст"""
        assert system_prompt is not None
        assert len(system_prompt) > 100
        assert "TMKI" in system_prompt
        assert "шахтостроение" in system_prompt or "горно" in system_prompt
    
    def test_system_prompt_rules(self, system_prompt):
        """Проверка: системный промпт содержит ключевые правила"""
        required_keywords = [
            "ТОЛЬКО на основе",
            "источник",
            "ФНП",
            "СП",
            "ГОСТ",
            "русском языке"
        ]
        for keyword in required_keywords:
            assert keyword in system_prompt, f"Промпт должен содержать '{keyword}'"
    
    def test_test_data_has_questions(self, test_data):
        """Проверка: тестовые данные содержат вопросы"""
        assert "tests" in test_data
        assert len(test_data["tests"]) >= 4
        for test in test_data["tests"]:
            assert "question" in test
            assert "expected_answer_contains" in test
    
    def test_citations_schema_format(self, citations_schema):
        """Проверка: схема цитирования содержит обязательные поля"""
        assert "format" in citations_schema
        format_spec = citations_schema["format"]
        assert "required_fields" in format_spec
        assert "doc_id" in format_spec["required_fields"]
        assert "page" in format_spec["required_fields"]
        assert "snippet" in format_spec["required_fields"]
    
    def test_qa_pairs_expected_docs(self, test_data):
        """Проверка: каждый тест ожидает хотя бы один документ"""
        for test in test_data["tests"]:
            if "expected_doc_ids" in test:
                assert len(test["expected_doc_ids"]) >= 1
            if "expected_citations_min" in test:
                assert test["expected_citations_min"] >= 1
    
    def test_test_data_ids_unique(self, test_data):
        """Проверка: ID тестов уникальны"""
        ids = [t["id"] for t in test_data["tests"]]
        assert len(ids) == len(set(ids)), "ID тестов должны быть уникальны"

class TestRAGSearch:
    """Тесты поиска (требуют запущенного сервиса)"""
    
    @pytest.fixture
    def test_data(self):
        return load_test_data()
    
    @pytest.mark.skipif(
        os.environ.get("TMKI_SKIP_INTEGRATION") == "1",
        reason="Интеграционные тесты отключены (TMKI_SKIP_INTEGRATION=1)",
    )
    def test_search_returns_results(self, test_data):
        """Проверка: /api/ask возвращает ответ (demo должно быть запущено)."""
        import requests
        port = int(os.environ.get("TMKI_DEMO_PORT", "8770"))
        query = test_data["tests"][0]["question"]
        response = requests.post(
            f"http://127.0.0.1:{port}/api/ask",
            json={"question": query, "corpus": "skru-2"},
            timeout=120,
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data

    @pytest.mark.skipif(
        os.environ.get("TMKI_SKIP_INTEGRATION") == "1",
        reason="Интеграционные тесты отключены",
    )
    def test_citations_format(self, test_data):
        """Проверка: цитаты в ответе /api/ask."""
        import requests
        port = int(os.environ.get("TMKI_DEMO_PORT", "8770"))
        query = test_data["tests"][0]["question"]
        response = requests.post(
            f"http://127.0.0.1:{port}/api/ask",
            json={"question": query},
            timeout=120,
        )
        data = response.json()
        citations = data.get("citations") or []
        if citations:
            cit = citations[0]
            assert any(k in cit for k in ("snippet", "file_name", "doc_id", "relative_path"))

class TestConfig:
    """Тесты конфигурации"""
    
    def test_env_file_exists(self):
        """Проверка: файл конфига существует"""
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "rag_config.env")
        assert os.path.exists(env_path), "config/rag_config.env не найден"
    
    def test_env_has_required_vars(self):
        """Проверка: конфиг содержит обязательные переменные"""
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "rag_config.env")
        with open(env_path, encoding="utf-8") as f:
            content = f.read()
        
        required_vars = [
            "OLLAMA_URL",
            "OLLAMA_BASE_URL",
            "OLLAMA_EMBEDDING_MODEL",
            "OLLAMA_MODEL",
            "TMKI_EMBEDDING_DIMS",
            "TMKI_CHUNK_SIZE",
            "TMKI_RERANK_ENABLED",
            "TMKI_INDEX_BACKEND",
            "TMKI_PGVECTOR_TABLE",
        ]
        for var in required_vars:
            assert var in content, f"Переменная {var} должна быть в конфиге"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
