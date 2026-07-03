"""Сессии диалога (паттерн mem0/Haystack): история, контекст документов, follow-up."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FOLLOW_UP = re.compile(
    r"(?:"
    r"^.{0,40}(?:пункт|подробн|ещё|еще|уточн|тот же|этот|тот документ|выше|ранее|"
    r"продолж|разверни|а что|а как|почему|зачем|когда|где именно)"
    r"|^(?:да|нет|ок|хорошо|спасибо|понятно)\b"
    r")",
    re.IGNORECASE,
)

_MAX_TURNS = 24
_MAX_HISTORY_FOR_LLM = 8


@dataclass
class ChatTurn:
    role: str
    content: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    doc_ids: list[str] = field(default_factory=list)
    intent: str = "qa"
    confidence: str = "low"
    at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatTurn":
        return cls(
            role=str(data.get("role") or "user"),
            content=str(data.get("content") or ""),
            citations=list(data.get("citations") or []),
            doc_ids=[str(x) for x in (data.get("doc_ids") or [])],
            intent=str(data.get("intent") or "qa"),
            confidence=str(data.get("confidence") or "low"),
            at=str(data.get("at") or ""),
        )


@dataclass
class ChatSession:
    session_id: str
    corpus_id: str
    turns: list[ChatTurn] = field(default_factory=list)
    active_doc_ids: list[str] = field(default_factory=list)
    active_paths: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "corpus_id": self.corpus_id,
            "turns": [t.to_dict() for t in self.turns],
            "active_doc_ids": self.active_doc_ids,
            "active_paths": self.active_paths,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatSession":
        turns = [ChatTurn.from_dict(t) for t in (data.get("turns") or []) if isinstance(t, dict)]
        return cls(
            session_id=str(data.get("session_id") or ""),
            corpus_id=str(data.get("corpus_id") or "skru-2"),
            turns=turns,
            active_doc_ids=[str(x) for x in (data.get("active_doc_ids") or [])],
            active_paths=[str(x) for x in (data.get("active_paths") or [])],
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


class ChatSessionStore:
    """In-memory + optional persist в artifacts/chat-sessions/."""

    def __init__(self, persist_dir: Path | None = None) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._persist_dir = persist_dir

    def _path(self, session_id: str) -> Path | None:
        if not self._persist_dir:
            return None
        return self._persist_dir / f"{session_id}.json"

    def _load_disk(self, session_id: str) -> ChatSession | None:
        path = self._path(session_id)
        if not path or not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ChatSession.from_dict(data)
        except (OSError, json.JSONDecodeError, TypeError):
            return None

    def _save_disk(self, session: ChatSession) -> None:
        if not self._persist_dir:
            return
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(session.session_id)
        if path:
            path.write_text(json.dumps(session.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, session_id: str) -> ChatSession | None:
        if session_id in self._sessions:
            return self._sessions[session_id]
        loaded = self._load_disk(session_id)
        if loaded:
            self._sessions[session_id] = loaded
        return loaded

    def create(self, *, corpus_id: str, session_id: str | None = None) -> ChatSession:
        sid = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        now = _now_iso()
        session = ChatSession(session_id=sid, corpus_id=corpus_id, created_at=now, updated_at=now)
        self._sessions[sid] = session
        self._save_disk(session)
        return session

    def get_or_create(self, session_id: str | None, *, corpus_id: str) -> ChatSession:
        if session_id:
            existing = self.get(session_id)
            if existing:
                if existing.corpus_id != corpus_id:
                    existing.corpus_id = corpus_id
                return existing
            return self.create(corpus_id=corpus_id, session_id=session_id)
        return self.create(corpus_id=corpus_id)

    def append_turn(self, session: ChatSession, turn: ChatTurn) -> None:
        session.turns.append(turn)
        if len(session.turns) > _MAX_TURNS:
            session.turns = session.turns[-_MAX_TURNS:]
        if turn.role == "assistant":
            ids = [c.get("doc_id") for c in turn.citations if c.get("doc_id")]
            paths = [c.get("relative_path") for c in turn.citations if c.get("relative_path")]
            if ids:
                session.active_doc_ids = list(dict.fromkeys(ids))[:8]
            if paths:
                session.active_paths = list(dict.fromkeys(paths))[:8]
        session.updated_at = _now_iso()
        self._sessions[session.session_id] = session
        self._save_disk(session)

    def history_for_llm(self, session: ChatSession) -> list[dict[str, str]]:
        """Последние реплики для Ollama/OpenAI messages (без цитат — они в новом user)."""
        out: list[dict[str, str]] = []
        for turn in session.turns[-_MAX_HISTORY_FOR_LLM:]:
            if turn.role not in ("user", "assistant"):
                continue
            text = (turn.content or "").strip()
            if not text:
                continue
            if turn.role == "assistant" and len(text) > 1200:
                text = text[:1200] + "…"
            out.append({"role": turn.role, "content": text})
        return out

    def session_memory_note(self, session: ChatSession) -> str:
        """Краткий контекст сессии для RAG/LLM (память диалога)."""
        if not session.turns:
            return ""
        lines: list[str] = []
        if session.active_paths:
            lines.append("Активные документы: " + "; ".join(session.active_paths[:4]))
        last_user = next((t.content for t in reversed(session.turns) if t.role == "user"), "")
        last_asst = next((t.content for t in reversed(session.turns) if t.role == "assistant"), "")
        if last_user:
            lines.append(f"Предыдущий вопрос: {last_user[:300]}")
        if last_asst:
            lines.append(f"Предыдущий ответ (кратко): {last_asst[:400]}")
        return "\n".join(lines)


def is_follow_up_query(query: str) -> bool:
    q = query.strip()
    if not q:
        return False
    if len(q) < 80 and _FOLLOW_UP.search(q):
        return True
    if len(q) < 35 and not any(ch.isdigit() for ch in q):
        words = q.split()
        if len(words) <= 8:
            return True
    return False


def augment_query_with_session(query: str, session: ChatSession) -> str:
    if not is_follow_up_query(query):
        return query
    note = ChatSessionStore().session_memory_note(session)
    if not note:
        return query
    return f"{query}\n\n[Контекст диалога]\n{note}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
