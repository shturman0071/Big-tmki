#!/usr/bin/env python3
"""
Пошаговая проверка TMKI Demo (для новичка).

Запуск:
  1. В одном окне PowerShell:  .\\start-demo.ps1
  2. В другом окне:             python scripts/check_demo.py

Или только автотест (demo должно быть запущено):
  python scripts/check_demo.py --auto
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME = os.path.join(ROOT, "runtime")
sys.path.insert(0, ROOT)
sys.path.insert(0, RUNTIME)

from tmki_runtime.rag_env import load_rag_config

load_rag_config(override=False)

DEMO_PORT = int(os.environ.get("TMKI_DEMO_PORT", "8770"))
DEMO_URL = f"http://127.0.0.1:{DEMO_PORT}"

# Вопросы привязаны к файлам в data/test_docs/
DEMO_QUESTIONS = [
    {
        "step": 1,
        "question": "письмо 274",
        "why": "Короткий запрос — должен найти «Письмо № 274 от 14.06.2022.pdf»",
        "expect_in_top": ["274", "письм"],
        "expect_digits_in_top": ["274"],
    },
    {
        "step": 2,
        "question": "документ о качестве 452",
        "why": "Основной документ в индексе (99 чанков)",
        "expect_in_top": ["452", "качеств"],
        "expect_digits_in_top": ["452"],
    },
    {
        "step": 3,
        "question": "протокол СС КС",
        "why": "Проверка поиска по DOCX",
        "expect_in_top": ["протокол", "сс", "кс"],
    },
    {
        "step": 4,
        "question": "замечания КМД армировка",
        "why": "Технический запрос по КМД",
        "expect_in_top": ["замечан", "кмд", "армиров"],
    },
    {
        "step": 5,
        "question": "Что такое глубина шахты Сатимол?",
        "why": "Негативный тест: такого докута нет — ответ должен быть честным",
        "expect_in_top": None,
        "expect_no_hallucination": True,
    },
]


def _ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def _warn(msg: str) -> None:
    print(f"  [!!]   {msg}")


def check_ollama() -> bool:
    print("\n=== Шаг 0a: Ollama (эмбеддинги и ответы) ===")
    try:
        import requests

        r = requests.get(f"{os.environ.get('OLLAMA_URL', 'http://localhost:11434')}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m.get("name", "") for m in r.json().get("models", [])]
        if any("nomic-embed" in m for m in models):
            _ok("Ollama запущен, nomic-embed-text найден")
        else:
            _warn("Ollama запущен, но nomic-embed-text не найден. Выполните: ollama pull nomic-embed-text")
        if any("qwen" in m for m in models):
            _ok("Модель qwen для ответов найдена")
        else:
            _warn("qwen не найден. Для ответов: ollama pull qwen2.5:7b")
        return True
    except Exception as exc:
        _fail(f"Ollama недоступен: {exc}")
        print("       Запустите Ollama: https://ollama.ai")
        return False


def check_database() -> bool:
    print("\n=== Шаг 0b: База данных (индекс чанков) ===")
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        _fail("DATABASE_URL не задан (см. config/rag_config.env)")
        return False
    try:
        import psycopg2

        conn = psycopg2.connect(url, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), MAX(embedding_dim) FROM chunks")
        count, dim = cur.fetchone()
        cur.execute(
            "SELECT corpus_id, COUNT(*) FROM chunks GROUP BY corpus_id ORDER BY COUNT(*) DESC"
        )
        by_corpus = cur.fetchall()
        conn.close()
        if count and count > 0:
            _ok(f"Таблица chunks: {count} чанков, размерность {dim}")
            for cid, n in by_corpus:
                label = cid or "(null)"
                _ok(f"  corpus {label}: {n}")
            if dim != 768:
                _warn(f"Ожидалась размерность 768, сейчас {dim}. Запустите: python scripts/reindex_all.py")
            return True
        _fail("Таблица chunks пуста. Запустите: python scripts/reindex_all.py")
        return False
    except Exception as exc:
        _fail(f"PostgreSQL недоступен: {type(exc).__name__}")
        print("       Проверьте, что Postgres запущен на порту 5433 (см. config/rag_config.env)")
        return False


def check_demo_server() -> bool:
    print(f"\n=== Шаг 0c: Demo-сервер ({DEMO_URL}) ===")
    try:
        import requests

        r = requests.get(f"{DEMO_URL}/api/status", timeout=15)
        if r.status_code != 200:
            _fail(f"Сервер ответил кодом {r.status_code}")
            return False
        data = r.json()
        _ok(f"Demo работает (backend={data.get('index_backend')}, строк={data.get('index_rows')})")
        return True
    except Exception as exc:
        _fail(f"Demo не отвечает: {exc}")
        print("       Запустите в отдельном окне: .\\start-demo.ps1")
        return False


def _hay(citation: dict) -> str:
    parts = [
        citation.get("file_name") or "",
        citation.get("snippet") or "",
        citation.get("relative_path") or "",
    ]
    return " ".join(parts).lower()


def _digits_in_citation(citation: dict) -> set[str]:
    """Извлечь числовые токены из имени файла и пути (для проверки № документа)."""
    from tmki_rag.match_score import filename_contains_doc_number

    raw = " ".join(
        [
            citation.get("file_name") or "",
            citation.get("relative_path") or "",
            citation.get("doc_id") or "",
        ]
    )
    nums = re.findall(r"\d{2,}", raw)
    return {n for n in nums if filename_contains_doc_number(raw, n)}


def _citation_matches_digits(citations: list[dict], required: list[str]) -> bool:
    if not citations or not required:
        return True
    name = " ".join(
        str(citations[0].get(k) or "")
        for k in ("file_name", "relative_path", "doc_id")
    )
    from tmki_rag.match_score import filename_contains_doc_number

    return all(filename_contains_doc_number(name, d) for d in required)


def ask_demo(question: str, *, llm: str | None = None, timeout: int = 180, corpus: str = "test_docs") -> dict:
    import requests

    payload: dict = {"question": question, "corpus": corpus}
    if llm:
        payload["llm"] = llm
    r = requests.post(f"{DEMO_URL}/api/ask", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def run_question_tests(*, use_stub: bool = False) -> tuple[int, int]:
    print("\n=== Шаги 1–5: Вопросы к demo (как в браузере) ===")
    if use_stub:
        print("  (режим stub — быстрые ответы без Ollama, только проверка поиска)\n")
    else:
        print("  (первый ответ может занять 1–2 минуты — грузится модель)\n")

    passed = 0
    llm = "stub" if use_stub else None

    for item in DEMO_QUESTIONS:
        step = item["step"]
        q = item["question"]
        print(f"--- Шаг {step} ---")
        print(f"Вопрос: «{q}»")
        print(f"Зачем: {item['why']}")
        try:
            t0 = time.time()
            data = ask_demo(q, llm=llm)
            elapsed = round(time.time() - t0, 1)
            citations = data.get("citations") or []
            answer = (data.get("answer") or "").strip()
            backend = data.get("backend", "?")
            print(f"Время: {elapsed} с | backend: {backend} | цитат: {len(citations)}")

            if citations:
                top = citations[0]
                fname = top.get("file_name") or top.get("doc_id") or "?"
                snippet = (top.get("snippet") or "")[:120]
                print(f"Топ-источник: {fname}")
                if snippet:
                    print(f"Фрагмент: {snippet}...")

            expect = item.get("expect_in_top")
            need_digits = item.get("expect_digits_in_top")
            step_ok = False
            if expect:
                hay = " ".join(_hay(c) for c in citations[:3])
                hit = any(e.lower() in hay for e in expect)
                digit_ok = _citation_matches_digits(citations, need_digits or [])
                if hit and citations and digit_ok:
                    _ok("Релевантный документ найден в топ-3")
                    step_ok = True
                elif hit and citations and need_digits and not digit_ok:
                    top = citations[0]
                    _fail(
                        f"Топ-источник не совпадает по номеру {need_digits}: "
                        f"{top.get('file_name') or top.get('doc_id')}"
                    )
                else:
                    _fail(f"В топ-3 нет ожидаемых слов: {expect}")
            elif item.get("expect_no_hallucination"):
                low = answer.lower()
                if not citations or "нет" in low or "не найден" in low or "не содержит" in low or len(answer) < 400:
                    _ok("Честный ответ без документа (или короткий stub)")
                    step_ok = True
                else:
                    _warn("Ответ длинный при отсутствии документа — проверьте вручную")
                    step_ok = True

            if step_ok:
                passed += 1

            if answer and not use_stub:
                print(f"Ответ (начало): {answer[:200]}...")
            print()
        except Exception as exc:
            _fail(str(exc))
            print()

    return passed, len(DEMO_QUESTIONS)


def print_manual_guide() -> None:
    print(
        """
╔══════════════════════════════════════════════════════════════╗
║  КАК ПРОВЕРИТЬ DEMO ВРУЧНУЮ (браузер)                        ║
╠══════════════════════════════════════════════════════════════╣
║  1. Откройте PowerShell в папке проекта                      ║
║  2. Запустите:  .\\start-demo.ps1                             ║
║  3. Дождитесь строки «Warmup: index ready» (1–2 мин)         ║
║  4. Откройте:   http://127.0.0.1:8770/                       ║
║  5. Введите вопросы по очереди (см. шаги 1–5 выше)           ║
║                                                              ║
║  На что смотреть в ответе:                                   ║
║    • Есть блок «Источники» / citations с именем файла        ║
║    • Текст ответа ссылается на найденные фрагменты           ║
║    • Если документа нет — система говорит об этом прямо      ║
╚══════════════════════════════════════════════════════════════╝
"""
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Пошаговая проверка TMKI Demo")
    parser.add_argument("--auto", action="store_true", help="Только автотест, без подсказок")
    parser.add_argument("--stub", action="store_true", help="Быстрый режим: поиск без Ollama-ответов")
    args = parser.parse_args()

    if not args.auto:
        print_manual_guide()

    infra_ok = check_ollama() & check_database()
    demo_ok = check_demo_server()
    if not demo_ok:
        print("\nИтог: сначала запустите demo (.\\start-demo.ps1), затем повторите проверку.")
        return 1

    passed, total = run_question_tests(use_stub=args.stub)
    print("=" * 60)
    print(f"ИТОГ: инфраструктура {'OK' if infra_ok else 'проблемы'} | вопросы {passed}/{total}")
    if passed == total and infra_ok:
        print("Demo работает корректно на тестовых документах.")
        return 0
    print("Есть замечания — см. [FAIL] и [!!] выше.")
    return 1 if passed < total or not infra_ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
