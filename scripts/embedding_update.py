import os
import json
import psycopg2
import requests
from tqdm import tqdm
from typing import List, Dict, Any
import time

# Загрузка конфига
def get_config(key: str, default: any = None) -> any:
    """Получить значение из переменных окружения"""
    return os.getenv(key, default)

# Загрузить .env файл если есть
def load_env():
    """Загрузить переменные из .env файла"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "rag_config.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

# Загружаем .env
load_env()

import sys as _sys
_runtime = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runtime")
_sys.path.insert(0, _runtime)
from tmki_runtime.rag_env import load_rag_config
load_rag_config(override=False)

# Конфигурация
OLLAMA_URL = get_config("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = get_config("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
EMBEDDING_DIM = int(get_config("TMKI_EMBEDDING_DIM", 768))
DB_URL = get_config("DATABASE_URL", "postgresql://user:pass@localhost:5432/tmki")
BATCH_SIZE = 50  # Количество чанков за один запрос к Ollama

def get_embedding(text: str) -> List[float]:
    """
    Получить эмбеддинг для текста через Ollama API
    
    Args:
        text: текст для эмбеддинга
    
    Returns:
        List[float]: вектор эмбеддинга
    """
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text},
            timeout=30
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении эмбеддинга: {e}")
        return None

def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Получить эмбеддинги для пачки текстов
    
    Args:
        texts: список текстов
    
    Returns:
        List[List[float]]: список векторов
    """
    embeddings = []
    for text in tqdm(texts, desc="Получение эмбеддингов"):
        embedding = get_embedding(text)
        if embedding:
            embeddings.append(embedding)
        else:
            embeddings.append(None)
        time.sleep(0.1)  # Задержка для избежания перегрузки Ollama
    return embeddings

def update_embeddings():
    """
    Обновить эмбеддинги для всех чанков в БД
    """
    print(f"Подключение к БД: {DB_URL}")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    # Проверка существования таблицы chunks
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'chunks'
        )
    """)
    table_exists = cur.fetchone()[0]
    
    if not table_exists:
        print("Таблица chunks не найдена. Создаём...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT,
                content TEXT,
                embedding vector(768),
                page INTEGER,
                section TEXT,
                metadata JSONB,
                indexed_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        print("Таблица создана. Нет чанков для обновления.")
        cur.close()
        conn.close()
        return
    
    # Получить все чанки
    cur.execute("""
        SELECT chunk_id, content FROM chunks
        WHERE embedding IS NULL OR embedding_dim != %s
    """, (EMBEDDING_DIM,))
    chunks = cur.fetchall()
    
    print(f"Найдено чанков для обновления: {len(chunks)}")
    
    if len(chunks) == 0:
        print("Все чанки уже имеют актуальные эмбеддинги.")
        cur.close()
        conn.close()
        return
    
    # Обновлять пачками
    total = len(chunks)
    updated = 0
    failed = 0
    
    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i:i+BATCH_SIZE]
        batch_ids = [chunk[0] for chunk in batch]
        batch_texts = [chunk[1] for chunk in batch]
        
        # Получить эмбеддинги для пачки
        embeddings = get_embeddings_batch(batch_texts)
        
        # Обновить БД
        for chunk_id, embedding in zip(batch_ids, embeddings):
            if embedding:
                # Конвертировать в строку для PostgreSQL vector
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                cur.execute(
                    """
                    UPDATE chunks 
                    SET embedding = %s::vector, 
                        embedding_dim = %s,
                        updated_at = NOW()
                    WHERE chunk_id = %s
                    """,
                    (embedding_str, EMBEDDING_DIM, chunk_id)
                )
                updated += 1
            else:
                failed += 1
        
        # Коммит после каждой пачки
        conn.commit()
        print(f"Прогресс: {updated}/{total} обновлено, {failed} ошибок")
    
    cur.close()
    conn.close()
    
    print(f"\n✅ Обновление завершено!")
    print(f"   Успешно обновлено: {updated}")
    print(f"   Ошибок: {failed}")
    print(f"   Размерность: {EMBEDDING_DIM}")

def check_ollama():
    """Проверить доступность Ollama"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
        models = [m["name"] for m in response.json().get("models", [])]
        print(f"✅ Ollama доступен. Модели: {models}")
        
        if EMBEDDING_MODEL not in [m.split(":")[0] for m in models]:
            print(f"⚠️ Модель {EMBEDDING_MODEL} не найдена. Установите:")
            print(f"   ollama pull {EMBEDDING_MODEL}")
            return False
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Ollama недоступен: {e}")
        print(f"   Убедитесь, что Ollama запущен на {OLLAMA_URL}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TMKI Embedding Update Tool")
    print("=" * 60)
    
    # Проверка Ollama
    if not check_ollama():
        print("\n⚠️ Исправьте проблемы с Ollama и запустите скрипт снова.")
        exit(1)
    
    print(f"\nМодель эмбеддингов: {EMBEDDING_MODEL}")
    print(f"Размерность: {EMBEDDING_DIM}")
    print(f"БД: {DB_URL}")
    print()
    
    # Обновить эмбеддинги
    update_embeddings()
