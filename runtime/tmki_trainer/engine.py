"""Движок обучалки: проверка ответов, прогресс, прогон через RAG/чат."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_TOKEN_RE = re.compile(r"[а-яёa-z0-9]{3,}", re.IGNORECASE)

_CURRICULUM_PATH = Path(__file__).resolve().parent / "curriculum.json"
_ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts" / "trainer"


@dataclass
class TrainerLesson:
    id: str
    skill: str
    question: str
    hint: str = ""
    expected_keywords: list[str] = field(default_factory=list)
    expected_intent: str = ""
    corpus_id: str = "skru-2"
    reference_answer: str = ""
    follow_up: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrainerLesson":
        return cls(
            id=str(data.get("id") or ""),
            skill=str(data.get("skill") or "search"),
            question=str(data.get("question") or ""),
            hint=str(data.get("hint") or ""),
            expected_keywords=[str(k).lower() for k in (data.get("expected_keywords") or [])],
            expected_intent=str(data.get("expected_intent") or ""),
            corpus_id=str(data.get("corpus_id") or "skru-2"),
            reference_answer=str(data.get("reference_answer") or ""),
            follow_up=data.get("follow_up") if isinstance(data.get("follow_up"), dict) else None,
        )


@dataclass
class TrainerTrack:
    id: str
    title: str
    description: str
    lessons: list[TrainerLesson]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrainerTrack":
        lessons = [TrainerLesson.from_dict(x) for x in (data.get("lessons") or []) if isinstance(x, dict)]
        return cls(
            id=str(data.get("id") or ""),
            title=str(data.get("title") or ""),
            description=str(data.get("description") or ""),
            lessons=lessons,
        )


@dataclass
class TrainerCurriculum:
    schema_version: str
    title: str
    description: str
    tracks: list[TrainerTrack]

    def lesson_by_id(self, lesson_id: str) -> TrainerLesson | None:
        for track in self.tracks:
            for lesson in track.lessons:
                if lesson.id == lesson_id:
                    return lesson
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "title": self.title,
            "description": self.description,
            "tracks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "lessons": [
                        {
                            "id": L.id,
                            "skill": L.skill,
                            "question": L.question,
                            "hint": L.hint,
                            "has_follow_up": bool(L.follow_up),
                            "corpus_id": L.corpus_id,
                        }
                        for L in t.lessons
                    ],
                }
                for t in self.tracks
            ],
        }


@dataclass
class TrainerAttemptResult:
    lesson_id: str
    skill: str
    score: float
    passed: bool
    feedback: str
    keyword_hits: list[str]
    keyword_misses: list[str]
    user_answer: str
    reference_answer: str
    system_answer: str | None = None
    system_intent: str | None = None
    citations_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "lesson_id": self.lesson_id,
            "skill": self.skill,
            "score": round(self.score, 3),
            "passed": self.passed,
            "feedback": self.feedback,
            "keyword_hits": self.keyword_hits,
            "keyword_misses": self.keyword_misses,
            "user_answer": self.user_answer,
            "reference_answer": self.reference_answer,
            "system_answer": self.system_answer,
            "system_intent": self.system_intent,
            "citations_count": self.citations_count,
        }


def load_curriculum(path: Path | None = None) -> TrainerCurriculum:
    src = path or _CURRICULUM_PATH
    data = json.loads(src.read_text(encoding="utf-8"))
    tracks = [TrainerTrack.from_dict(t) for t in (data.get("tracks") or []) if isinstance(t, dict)]
    return TrainerCurriculum(
        schema_version=str(data.get("schema_version") or "0.1"),
        title=str(data.get("title") or "TMKI Trainer"),
        description=str(data.get("description") or ""),
        tracks=tracks,
    )


def _progress_path(user_id: str) -> Path:
    safe = re.sub(r"[^\w\-]", "_", user_id or "default")[:64]
    return _ARTIFACTS / f"progress-{safe}.json"


def load_progress(user_id: str = "default") -> dict[str, Any]:
    path = _progress_path(user_id)
    if not path.is_file():
        return {"user_id": user_id, "attempts": {}, "completed": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"user_id": user_id, "attempts": {}, "completed": []}


def record_attempt(user_id: str, lesson_id: str, result: TrainerAttemptResult) -> dict[str, Any]:
    progress = load_progress(user_id)
    attempts = progress.setdefault("attempts", {})
    if not isinstance(attempts, dict):
        attempts = {}
        progress["attempts"] = attempts
    history = attempts.get(lesson_id) or []
    if not isinstance(history, list):
        history = []
    history.append(
        {
            "at": _now_iso(),
            "score": result.score,
            "passed": result.passed,
        }
    )
    attempts[lesson_id] = history[-20:]
    completed = progress.setdefault("completed", [])
    if result.passed and lesson_id not in completed:
        completed.append(lesson_id)
    progress["updated_at"] = _now_iso()
    path = _progress_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")
    return progress


def _keyword_score(text: str, keywords: list[str]) -> tuple[float, list[str], list[str]]:
    if not keywords:
        return 1.0, [], []
    lowered = text.lower()
    tokens = set(_TOKEN_RE.findall(lowered))
    hits: list[str] = []
    misses: list[str] = []
    for kw in keywords:
        kw_l = kw.lower()
        if kw_l in lowered or any(kw_l in t or t in kw_l for t in tokens):
            hits.append(kw)
        else:
            misses.append(kw)
    score = len(hits) / len(keywords) if keywords else 1.0
    return score, hits, misses


def evaluate_attempt(
    lesson: TrainerLesson,
    user_answer: str,
    *,
    reference: str | None = None,
    pass_threshold: float = 0.55,
) -> TrainerAttemptResult:
    ref = (reference or lesson.reference_answer or "").strip()
    kw_score, hits, misses = _keyword_score(user_answer, lesson.expected_keywords)
    ref_score = 0.0
    if ref:
        ref_score, ref_hits, _ = _keyword_score(user_answer, _TOKEN_RE.findall(ref.lower())[:12])
        hits = list(dict.fromkeys(hits + ref_hits))
    score = kw_score * 0.7 + ref_score * 0.3 if ref else kw_score
    passed = score >= pass_threshold and (not lesson.expected_keywords or len(hits) >= max(1, len(lesson.expected_keywords) // 2))

    if passed:
        feedback = "Верно: ключевые идеи отражены. Сравните с ответом системы (кнопка «Спросить TMKI»)."
    elif hits:
        feedback = f"Частично ({int(score * 100)}%). Добавьте: {', '.join(misses[:4])}."
    else:
        feedback = f"Пока мало совпадений ({int(score * 100)}%). Подсказка: {lesson.hint or 'см. эталон'}"

    return TrainerAttemptResult(
        lesson_id=lesson.id,
        skill=lesson.skill,
        score=score,
        passed=passed,
        feedback=feedback,
        keyword_hits=hits,
        keyword_misses=misses,
        user_answer=user_answer.strip(),
        reference_answer=ref or lesson.hint,
    )


def run_system_practice(
    lesson: TrainerLesson,
    *,
    session_id: str | None = None,
    follow_up: bool = False,
) -> dict[str, Any]:
    """Прогон урока через RAG/чат — эталон для обучалки."""
    from tmki_demo.qa import analyze_document, chat_message, ask_regulations
    from tmki_rag.retrieval import detect_query_intent

    q = lesson.question
    if follow_up and lesson.follow_up:
        q = str(lesson.follow_up.get("question") or q)

    intent = detect_query_intent(q)
    if lesson.skill == "understand" and lesson.expected_intent in ("analyze", "summarize"):
        out = analyze_document(q, corpus_id=lesson.corpus_id)
    elif lesson.skill == "dialogue" or session_id or follow_up:
        out = chat_message(q, session_id=session_id, corpus_id=lesson.corpus_id)
    else:
        out = ask_regulations(q, corpus_id=lesson.corpus_id)

    out["practice_query"] = q
    out["detected_intent"] = intent
    if lesson.expected_intent and out.get("intent"):
        out["intent_match"] = out.get("intent") == lesson.expected_intent
    return out


def trainer_snapshot(user_id: str = "default") -> dict[str, Any]:
    curriculum = load_curriculum()
    progress = load_progress(user_id)
    total = sum(len(t.lessons) for t in curriculum.tracks)
    completed = len(progress.get("completed") or [])
    from tmki_document.reader import format_support_matrix

    return {
        "curriculum": curriculum.to_dict(),
        "progress": {
            "user_id": user_id,
            "completed": completed,
            "total_lessons": total,
            "percent": round(100.0 * completed / total, 1) if total else 0,
            "lesson_ids": progress.get("completed") or [],
        },
        "format_matrix": format_support_matrix()[:12],
        "skills": [
            {"id": "search", "label": "Поиск", "icon": "🔍"},
            {"id": "read", "label": "Чтение форматов", "icon": "📄"},
            {"id": "understand", "label": "Смысл документа", "icon": "🧠"},
            {"id": "dialogue", "label": "Диалог", "icon": "💬"},
        ],
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
