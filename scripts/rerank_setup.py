import os
import sys
import subprocess
import torch
from typing import List, Dict, Any

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

def check_pytorch():
    """Проверить версию PyTorch"""
    print("=" * 60)
    print("Проверка PyTorch")
    print("=" * 60)
    
    version = torch.__version__
    print(f"PyTorch version: {version}")
    
    if torch.cuda.is_available():
        print(f"CUDA доступен: {torch.cuda.get_device_name(0)}")
    else:
        print("CUDA не доступен (будет использоваться CPU)")
    
    # Проверка версии
    major, minor = version.split(".")[:2]
    if int(major) >= 2 and int(minor) >= 4:
        print("✅ PyTorch версия подходит (>= 2.4.0)")
        return True
    else:
        print("⚠️ PyTorch версия ниже 2.4.0. Рекомендуется обновить:")
        print("   pip install --upgrade torch")
        return False

def install_cross_encoder():
    """Установить cross-encoder модель"""
    print("\n" + "=" * 60)
    print("Установка Cross-Encoder модели")
    print("=" * 60)
    
    model_name = get_config("TMKI_RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    print(f"Модель: {model_name}")
    
    try:
        from sentence_transformers import CrossEncoder
        print("⏳ Загрузка модели (первый раз может занять несколько минут)...")
        model = CrossEncoder(model_name)
        print("✅ Cross-encoder модель успешно загружена!")
        return True
    except ImportError:
        print("❌ sentence-transformers не установлен. Установка...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers"])
        print("✅ sentence-transformers установлен. Повторите запуск.")
        return False
    except Exception as e:
        print(f"❌ Ошибка загрузки модели: {e}")
        return False

def test_rerank():
    """Протестировать rerank на примере"""
    print("\n" + "=" * 60)
    print("Тестирование Rerank")
    print("=" * 60)
    
    try:
        from sentence_transformers import CrossEncoder
        
        model_name = get_config("TMKI_RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        model = CrossEncoder(model_name)
        
        # Тестовые данные
        query = "маркшейдерская съёмка участок КС"
        candidates = [
            "Маркшейдерская съёмка на участке КС выполняется по регламенту",
            "Буровзрывные работы на шахте проводятся по графику",
            "Требования к маркшейдерским работам в горных выработках",
            "Правила безопасности при подземных работах"
        ]
        
        pairs = [(query, doc) for doc in candidates]
        scores = model.predict(pairs)
        
        print(f"Запрос: {query}")
        print("\nРезультаты ранжирования:")
        for doc, score in sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True):
            print(f"  {score:.4f}: {doc}")
        
        print("\n✅ Rerank работает корректно!")
        return True
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

def update_config():
    """Обновить конфиг с включённым rerank"""
    print("\n" + "=" * 60)
    print("Обновление конфига")
    print("=" * 60)
    
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "rag_config.env")
    
    if not os.path.exists(config_path):
        print("⚠️ Файл конфига не найден. Создайте config/rag_config.env")
        return False
    
    # Проверить, включён ли rerank
    with open(config_path) as f:
        content = f.read()
    
    if "TMKI_RERANK_ENABLED=1" in content:
        print("✅ Rerank уже включён в конфиге")
        return True
    
    # Добавить настройки
    with open(config_path, "a") as f:
        f.write("\n# Rerank (включён скриптом rerank_setup.py)\n")
        f.write("TMKI_RERANK_ENABLED=1\n")
    
    print("✅ Rerank включён в конфиге")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("TMKI Cross-Encoder Rerank Setup")
    print("=" * 60)
    
    # 1. Проверка PyTorch
    pytorch_ok = check_pytorch()
    if not pytorch_ok:
        print("\n⚠️ Рекомендуется обновить PyTorch для лучшей производительности")
    
    # 2. Установка модели
    model_ok = install_cross_encoder()
    if not model_ok:
        print("\n❌ Не удалось установить cross-encoder модель")
        sys.exit(1)
    
    # 3. Тестирование
    test_ok = test_rerank()
    if not test_ok:
        print("\n⚠️ Тестирование не пройдено, но установка завершена")
    
    # 4. Обновление конфига
    config_ok = update_config()
    
    print("\n" + "=" * 60)
    if model_ok and test_ok:
        print("✅ Cross-encoder готов к использованию!")
        print("   TMKI_RERANK_ENABLED=1")
        print("   TMKI_RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2")
        print("\n   Запустите переиндексацию и тесты.")
    else:
        print("⚠️ Настройка завершена с ошибками. Проверьте логи.")
    print("=" * 60)
