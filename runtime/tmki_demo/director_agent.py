"""Даша — голосовой агент управленческого дашборда."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

AGENT_NAME = "Даша"

_CLARIFY_MARKERS = (
    "уточните",
    "уточни",
    "поясните",
    "не совсем понял",
    "не понял",
    "какой именно",
    "что именно",
    "о чём",
    "о чем",
)


def _needs_clarification(question: str, *, has_document: bool) -> bool:
    if has_document:
        return False
    q = (question or "").strip()
    if len(q) < 8:
        return True
    if re.match(r"^(что|как|где|когда|почему|зачем|ну|а|и|это)\s*\??$", q, re.I):
        return True
    if re.match(r"^(помоги|подскажи|расскажи)\s*\??$", q, re.I):
        return True
    return False


def _clarifying_reply() -> str:
    return (
        "Уточните, пожалуйста: вас интересуют договоры, просрочки, риски, финансы "
        "или конкретный объект проекта?"
    )


def _dashboard_brief() -> str:
    from tmki_demo.director_dashboard import build_director_dashboard

    d = build_director_dashboard()
    contracts = d.get("contracts") or []
    overdue = d.get("overdue_items") or []
    risks = d.get("risks") or []
    debtors = d.get("debtors") or []
    amount = sum(float(c.get("amount") or 0) for c in contracts)
    debt = sum(float(x.get("overdue") or 0) for x in debtors)
    high_risks = sum(1 for r in risks if str(r.get("level") or "") in ("Критичный", "Высокий"))
    return (
        f"Проект: {d.get('project') or 'Сатимол'}. "
        f"Договоров: {len(contracts)}, сумма портфеля около {amount:.0f} млн ₽. "
        f"Просрочек: {len(overdue)}. Рисков высокого уровня: {high_risks}. "
        f"Дебиторка: {debt:.0f} млн ₽."
    )


def _resolve_relative_path(document: dict[str, Any], corpus_id: str) -> str:
    rel = (document.get("relative_path") or "").strip()
    if rel:
        return rel
    abs_path = (document.get("absolute_path") or document.get("path") or "").strip()
    if not abs_path:
        return ""
    name = Path(abs_path).name
    try:
        from tmki_demo.qa import _get_catalog

        catalog = _get_catalog(corpus_id=corpus_id)
        for match in catalog.search_paths(name, limit=12):
            match_abs = str(match.get("absolute_path") or "")
            if match_abs and Path(match_abs).resolve() == Path(abs_path).resolve():
                return str(match.get("relative_path") or "").strip()
        for match in catalog.search_paths(name, limit=3):
            found = str(match.get("relative_path") or "").strip()
            if found:
                return found
    except Exception:
        pass
    return name


def _answer_general(question: str, *, llm: str, history: list[dict[str, str]] | None) -> str:
    from tmki_demo.doc_voice import _llm_text, _strip_voice_boilerplate

    brief = _dashboard_brief()
    prompt = (
        f"Ты — {AGENT_NAME}, помощник руководителя инженерной компании ТМКИ.\n"
        f"Контекст дашборда: {brief}\n\n"
        f"Вопрос: {question}\n\n"
        "Ответь по-русски, 2–4 предложения, логично и по делу. "
        "Не указывай названия файлов, doc_id, ссылки и источники. "
        "Если вопрос слишком общий — задай один короткий уточняющий вопрос."
    )
    answer = _strip_voice_boilerplate(
        _llm_text(prompt=prompt, citations=[], llm=llm, history=history, mode="voice")
    )
    return answer or "Пока не могу сформулировать ответ. Переформулируйте вопрос, пожалуйста."


def _answer_about_synth_document(
    question: str,
    *,
    document: dict[str, Any],
    llm: str,
    history: list[dict[str, str]] | None,
) -> str | None:
    from tmki_demo.doc_voice import _llm_text, _strip_voice_boilerplate
    from tmki_demo.synthetic_docs import read_text, root_path

    abs_path = (document.get("absolute_path") or document.get("path") or "").strip()
    if not abs_path:
        return None
    try:
        path = Path(abs_path).resolve()
        root = root_path().resolve()
        if root not in path.parents and path != root:
            return None
    except OSError:
        return None
    content = read_text(path)
    if not content:
        return None
    prompt = (
        f"Ты — {AGENT_NAME}. Ниже текст синтетического документа дашборда.\n"
        f"Файл: {path.name}\n\n---\n{content}\n---\n\n"
        f"Вопрос: {question}\n\n"
        "Ответь по-русски кратко (2–5 предложений) строго по тексту документа."
    )
    answer = _strip_voice_boilerplate(
        _llm_text(prompt=prompt, citations=[], llm=llm, history=history, mode="voice")
    )
    return answer or "По этому документу пока нет ответа. Уточните вопрос."


def _answer_about_document(
    question: str,
    *,
    document: dict[str, Any],
    corpus_id: str,
    llm: str,
    history: list[dict[str, str]] | None,
) -> str:
    from tmki_demo.doc_voice import _answer_voice_question, _strip_voice_boilerplate

    synth = _answer_about_synth_document(
        question, document=document, llm=llm, history=history
    )
    if synth:
        return synth

    rel = _resolve_relative_path(document, corpus_id)
    if not rel:
        return "Не удалось определить документ. Откройте файл из списка поиска ещё раз."
    answer = _answer_voice_question(
        question=question,
        corpus_id=corpus_id,
        relative_path=rel,
        llm=llm,
        history=history,
    )
    answer = _strip_voice_boilerplate(answer)
    if not answer or "нет ответа" in answer.lower():
        return (
            "По этому документу в доступных фрагментах ответа нет. "
            "Уточните, что именно вас интересует в документе?"
        )
    return answer


def _pack(answer: str, *, llm: str, clarify: bool = False) -> dict[str, Any]:
    from tmki_demo.doc_voice import synthesize_tts_payload

    text = (answer or "").strip()
    low = text.lower()
    if not clarify and text.endswith("?") and any(m in low for m in _CLARIFY_MARKERS):
        clarify = True
    return {
        "agent": AGENT_NAME,
        "answer": text,
        "clarify": clarify,
        "tts": synthesize_tts_payload(text),
        "llm_provider": llm,
    }


def director_agent_chat(body: dict[str, Any]) -> dict[str, Any]:
    llm = str(body.get("llm") or "ollama").lower()
    corpus_id = str(body.get("corpus") or body.get("corpus_id") or "skru-2")
    history = body.get("history") if isinstance(body.get("history"), list) else []
    document = body.get("document") if isinstance(body.get("document"), dict) else None
    has_doc = bool(document and (document.get("relative_path") or document.get("absolute_path") or document.get("path")))

    if body.get("greeting"):
        name = (body.get("user_name") or "").strip()
        hello = f"Здравствуйте{', ' + name if name else ''}! Я {AGENT_NAME}, ваш помощник на дашборде. Задайте вопрос голосом или текстом."
        return _pack(hello, llm=llm)

    question = str(body.get("question") or "").strip()
    if not question:
        return _pack("Напишите или скажите ваш вопрос.", llm=llm, clarify=True)

    if _needs_clarification(question, has_document=has_doc):
        return _pack(_clarifying_reply(), llm=llm, clarify=True)

    if has_doc and document is not None:
        answer = _answer_about_document(
            question,
            document=document,
            corpus_id=corpus_id,
            llm=llm,
            history=history,
        )
        return _pack(answer, llm=llm)

    # Если вопрос похож на поиск договора / to-do — подмешиваем синтетические файлы в ответ.
    low_q = question.lower()
    if any(k in low_q for k in ("договор", "контракт", "todo", "to-do", "туду", "дела")):
        try:
            from tmki_demo.synthetic_docs import search as synth_search

            hits = synth_search(question, limit=3)
            if hits:
                names = ", ".join(h["file_name"] for h in hits)
                brief = _answer_general(question, llm=llm, history=history)
                extra = f" Нашёл связанные файлы: {names}. Могу открыть любой из них."
                return _pack((brief + extra).strip(), llm=llm)
        except Exception:
            pass

    answer = _answer_general(question, llm=llm, history=history)
    return _pack(answer, llm=llm)
