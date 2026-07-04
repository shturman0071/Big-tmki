import os
import sys
import json
import psycopg2
import requests
from tqdm import tqdm
from typing import List, Dict, Any
import hashlib
from datetime import datetime

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Загрузка конфига
def get_config(key: str, default: any = None) -> any:
    return os.getenv(key, default)

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "rag_config.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

load_env()

# Импорт модулей
try:
    from scripts.chunking_config import process_document, get_document_metadata
except ImportError:
    print("⚠️ Не удалось импортировать chunking_config. Убедитесь, что файл существует.")
    sys.exit(1)

# Конфигурация
OLLAMA_URL = get_config("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = get_config("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
EMBEDDING_DIM = int(get_config("TMKI_EMBEDDING_DIM", 768))
DB_URL = get_config("DATABASE_URL", "postgresql://user:pass@localhost:5432/tmki")
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test_docs")

def get_embedding(text: str) -> List[float]:
    """Получить эмбеддинг через Ollama"""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text},
            timeout=30
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        print(f"Ошибка эмбеддинга: {e}")
        return None

def chunk_id_from_content(text: str, doc_id: str, page: int) -> str:
    """Создать stable ID для чанка"""
    content_hash = hashlib.md5(f"{doc_id}:{page}:{text[:100]}".encode()).hexdigest()[:12]
    return f"chunk_{content_hash}"

def init_db():
    """Создать таблицы если их нет"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    # Проверка расширения vector
    cur.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
    has_vector = cur.fetchone()[0]
    
    if not has_vector:
        print("⚠️ Расширение vector не установлено. Установка...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
        print("✅ Расширение vector установлено")
    
    # Создание таблицы chunks
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            doc_id TEXT,
            doc_path TEXT,
            content TEXT,
            embedding vector(%s),
            embedding_dim INTEGER,
            page INTEGER,
            section TEXT,
            has_table BOOLEAN DEFAULT FALSE,
            metadata JSONB,
            indexed_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """, (EMBEDDING_DIM,))
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Таблица chunks готова")

def find_documents(directory: str) -> List[str]:
    """Найти все документы в папке"""
    supported_ext = ('.pdf', '.docx', '.txt', '.md')
    docs = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(supported_ext):
                docs.append(os.path.join(root, file))
    return docs

def reindex_all():
    """Переиндексировать все документы"""
    print("=" * 60)
    print("TMKI Reindex Tool")
    print("=" * 60)
    
    # Проверка Ollama
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
        print(f"✅ Ollama доступен на {OLLAMA_URL}")
    except Exception as e:
        print(f"❌ Ollama недоступен: {e}")
        sys.exit(1)
    
    # Подготовка БД
    init_db()
    
    # Найти документы
    if not os.path.exists(DOCS_DIR):
        print(f"⚠️ Папка {DOCS_DIR} не существует. Создаём...")
        os.makedirs(DOCS_DIR)
        print(f"📁 Поместите документы в {DOCS_DIR} и запустите скрипт снова.")
        sys.exit(0)
    
    docs = find_documents(DOCS_DIR)
    if not docs:
        print(f"⚠️ Нет поддерживаемых документов в {DOCS_DIR}")
        print("   Поддерживаемые форматы: .pdf, .docx, .txt, .md")
        sys.exit(0)
    
    print(f"\nНайдено документов: {len(docs)}")
    for doc in docs:
        print(f"  - {os.path.basename(doc)}")
    
    # Подключение к БД
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    total_chunks = 0
    total_docs = len(docs)
    
    for idx, doc_path in enumerate(docs, 1):
        print(f"\n[{idx}/{total_docs}] Обработка: {os.path.basename(doc_path)}")
        
        try:
            # Получить чанки через Docling
            chunks = process_document(doc_path)
            print(f"  Извлечено чанков: {len(chunks)}")
            
            if not chunks:
                print("  ⚠️ Чанки не извлечены. Пропускаем.")
                continue
            
            # Получить эмбеддинги для каждого чанка
            doc_chunks = 0
            for chunk_data in tqdm(chunks, desc="  Индексация"):
                text = chunk_data["text"]
                metadata = chunk_data["metadata"]
                
                # Получить эмбеддинг
                embedding = get_embedding(text)
                if embedding is None:
                    print("  ⚠️ Пропуск чанка (ошибка эмбеддинга)")
                    continue
                
                # Создать chunk_id
                chunk_id = chunk_id_from_content(text, metadata["doc_id"], metadata["page"])
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                
                # Сохранить в БД
                cur.execute("""
                    INSERT INTO chunks (
                        chunk_id, doc_id, doc_path, content, embedding, 
                        embedding_dim, page, section, has_table, metadata,
                        indexed_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s::vector, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        embedding_dim = EXCLUDED.embedding_dim,
                        page = EXCLUDED.page,
                        section = EXCLUDED.section,
                        has_table = EXCLUDED.has_table,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                """, (
                    chunk_id,
                    metadata["doc_id"],
                    metadata["doc_path"],
                    text,
                    embedding_str,
                    EMBEDDING_DIM,
                    metadata["page"],
                    metadata.get("section"),
                    metadata.get("has_table", False),
                    json.dumps(metadata)
                ))
                
                doc_chunks += 1
                total_chunks += 1
                
                # Коммит каждые 50 чанков
                if doc_chunks % 50 == 0:
                    conn.commit()
            
            conn.commit()
            print(f"  ✅ Проиндексировано: {doc_chunks} чанков")
            
        except Exception as e:
            print(f"  ❌ Ошибка при обработке: {e}")
            continue
    
    cur.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Переиндексация завершена!")
    print(f"   Документов обработано: {total_docs}")
    print(f"   Всего чанков в индексе: {total_chunks}")
    print(f"   Размерность эмбеддингов: {EMBEDDING_DIM}")
    print("=" * 60)

if __name__ == "__main__":
    reindex_all()
