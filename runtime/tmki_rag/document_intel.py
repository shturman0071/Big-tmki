"""Document Intelligence: память по документам, анализ сути и ключевых пунктов."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LETTER_HINTS = re.compile(r"письм|правк|letter|correspondence|корреспонд", re.IGNORECASE)
_DRAWING_HINTS = re.compile(r"черт[её]ж|кмд|кж|схем|dwg|\.dxf", re.IGNORECASE)
_REMARKS_HINTS = re.compile(r"замечан", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[а-яёa-z0-9]{2,}", re.IGNORECASE)

_ANALYZE_INTENT = re.compile(
    r"(?:"
    r"проанализируй|анализ\s+документа|разбери\s+документ|"
    r"выдели\s+главн|что\s+главн|самое\s+главн|"
    r"запомни\s+документ|сохрани\s+анализ"
    r")",
    re.IGNORECASE,
)


@dataclass
class DocumentProfile:
    doc_id: str
    relative_path: str
    gist: str
    key_points: list[str] = field(default_factory=list)
    doc_type: str = "прочее"
    content_fingerprint: str = ""
    analyzed_at: str = ""
    llm_provider: str = "stub"
    corpus_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentProfile":
        return cls(
            doc_id=str(data.get("doc_id") or ""),
            relative_path=str(data.get("relative_path") or ""),
            gist=str(data.get("gist") or ""),
            key_points=[str(x) for x in (data.get("key_points") or [])],
            doc_type=str(data.get("doc_type") or "прочее"),
            content_fingerprint=str(data.get("content_fingerprint") or ""),
            analyzed_at=str(data.get("analyzed_at") or ""),
            llm_provider=str(data.get("llm_provider") or "stub"),
            corpus_id=str(data.get("corpus_id") or ""),
        )


@dataclass
class ParsedAnalysis:
    gist: str
    key_points: list[str]
    doc_type: str
    raw_answer: str = ""

    def format_answer(self, *, file_name: str = "") -> str:
        lines = []
        if file_name:
            lines.append(f"Документ: {file_name}")
        if self.gist:
            lines.append(f"\nСуть: {self.gist}")
        if self.key_points:
            lines.append("\nГлавное:")
            lines.extend(f"• {p}" for p in self.key_points)
        if self.doc_type and self.doc_type != "прочее":
            lines.append(f"\nТип: {self.doc_type}")
        return "\n".join(lines).strip() or self.raw_answer


class DocumentMemoryStore:
    """Локальная «память» по doc_id — кэш анализа в artifacts."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._profiles: dict[str, DocumentProfile] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        entries = data.get("profiles") or {}
        if isinstance(entries, dict):
            for doc_id, item in entries.items():
                if isinstance(item, dict):
                    self._profiles[str(doc_id)] = DocumentProfile.from_dict(item)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "0.1",
            "updated_at": _now_iso(),
            "profiles": {k: v.to_dict() for k, v in self._profiles.items()},
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, doc_id: str) -> DocumentProfile | None:
        return self._profiles.get(doc_id)

    def put(self, profile: DocumentProfile) -> None:
        self._profiles[profile.doc_id] = profile
        self.save()

    def count(self) -> int:
        return len(self._profiles)


def profiles_path(artifacts_dir: Path) -> Path:
    return artifacts_dir / "doc-profiles.json"


def detect_analyze_intent(query: str) -> bool:
    return bool(_ANALYZE_INTENT.search(query.strip()))


def rank_file_matches_for_content_query(
    query: str,
    matches: list[dict[str, Any]],
    *,
    prefer_letters: bool = False,
) -> list[dict[str, Any]]:
    """Повысить релевантность писем/правок при запросе «опиши письмо …452»."""
    if not matches:
        return []
    q_lower = query.lower()
    tokens = [t for t in _TOKEN_RE.findall(q_lower) if len(t) >= 2]
    doc_nums = [t for t in tokens if any(ch.isdigit() for ch in t) and len(t) >= 2]

    def score_item(item: dict[str, Any]) -> float:
        base = float(item.get("score") or 0.0)
        path = (item.get("relative_path") or "").lower()
        name = (item.get("file_name") or "").lower()
        target = f"{path} {name}"
        if prefer_letters or "письм" in q_lower or "текст" in q_lower:
            if _LETTER_HINTS.search(target):
                base += 4.0
            if _REMARKS_HINTS.search(target) and not _LETTER_HINTS.search(target):
                base -= 2.5
        for num in doc_nums:
            if num in target:
                base += 2.0
        if _DRAWING_HINTS.search(target) and not prefer_letters:
            base += 0.5
        return base

    ranked = sorted(matches, key=score_item, reverse=True)
    out: list[dict[str, Any]] = []
    for item in ranked:
        copy = dict(item)
        copy["score"] = round(score_item(item), 3)
        out.append(copy)
    return out


def fingerprint_chunks(chunks: list[dict[str, Any]]) -> str:
    parts = sorted(
        f"{c.get('chunk_id') or ''}:{(c.get('content_preview') or '')[:120]}"
        for c in chunks
    )
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return f"sha256:{digest[:16]}"


def collect_chunks_for_doc(
    chunks: list[dict[str, Any]],
    *,
    doc_id: str | None = None,
    relative_path: str | None = None,
) -> list[dict[str, Any]]:
    rel = (relative_path or "").replace("\\", "/").lower()
    matched: list[dict[str, Any]] = []
    for chunk in chunks:
        cid = chunk.get("doc_id") or ""
        cr = (chunk.get("source_relative_path") or "").replace("\\", "/").lower()
        if doc_id and cid == doc_id:
            matched.append(chunk)
        elif rel and (cr == rel or rel in cr):
            matched.append(chunk)
    return matched


def select_analysis_chunks(
    chunks: list[dict[str, Any]],
    *,
    max_chunks: int = 12,
    max_chars: int = 12000,
) -> list[dict[str, Any]]:
    """Лучшие фрагменты документа для LLM-анализа (качество текста, длина)."""
    from tmki_rag.retrieval import chunk_text_quality

    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        text = (chunk.get("content_preview") or "").strip()
        if not text:
            continue
        quality = chunk_text_quality(text)
        if quality < 0.15:
            continue
        scored.append((quality * min(len(text), 800), chunk))
    scored.sort(key=lambda x: x[0], reverse=True)

    selected: list[dict[str, Any]] = []
    total = 0
    for _, chunk in scored:
        text = (chunk.get("content_preview") or "").strip()
        if total + len(text) > max_chars and selected:
            break
        selected.append(chunk)
        total += len(text)
        if len(selected) >= max_chunks:
            break
    if not selected and chunks:
        selected = chunks[: min(6, len(chunks))]
    return selected


def chunks_to_citations(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for chunk in chunks:
        citations.append(
            {
                "doc_id": chunk.get("doc_id") or "",
                "snippet": (chunk.get("content_preview") or "")[:1200],
                "file_name": Path(chunk.get("source_relative_path") or "").name,
                "relative_path": chunk.get("source_relative_path") or "",
            }
        )
    return citations


def parse_analysis_text(text: str) -> ParsedAnalysis:
    """Разбор ответа LLM в структуру (СУТЬ / ГЛАВНОЕ / ТИП)."""
    raw = (text or "").strip()
    gist = ""
    doc_type = "прочее"
    key_points: list[str] = []

    gist_m = re.search(r"(?:СУТЬ|Суть)\s*:\s*(.+?)(?=\n(?:ГЛАВНОЕ|Главное|ТИП|Тип)\s*:|$)", raw, re.DOTALL | re.IGNORECASE)
    if gist_m:
        gist = " ".join(gist_m.group(1).split())

    type_m = re.search(r"(?:ТИП|Тип)\s*:\s*(.+?)$", raw, re.IGNORECASE | re.MULTILINE)
    if type_m:
        doc_type = type_m.group(1).strip().rstrip(".")

    main_block = re.search(
        r"(?:ГЛАВНОЕ|Главное)\s*:\s*(.+?)(?=\n(?:ТИП|Тип)\s*:|$)",
        raw,
        re.DOTALL | re.IGNORECASE,
    )
    if main_block:
        block = main_block.group(1)
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            line = re.sub(r"^[-•*]\s*", "", line)
            line = re.sub(r"^\d+[.)]\s*", "", line)
            if line:
                key_points.append(line)

    if not gist and not key_points:
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if lines:
            gist = lines[0][:500]
            key_points = [ln.lstrip("-•* ") for ln in lines[1:8] if ln.lstrip("-•* ")]

    return ParsedAnalysis(gist=gist, key_points=key_points[:8], doc_type=doc_type, raw_answer=raw)


def infer_doc_type_from_path(relative_path: str) -> str:
    target = relative_path.lower()
    if _LETTER_HINTS.search(target):
        return "письмо"
    if _DRAWING_HINTS.search(target):
        return "чертёж"
    if _REMARKS_HINTS.search(target):
        return "замечания"
    if "ттн" in target or "накладн" in target:
        return "ТТН"
    if "акт" in target:
        return "акт"
    return "прочее"


def low_text_coverage_hint(chunks: list[dict[str, Any]]) -> str | None:
    """Подсказка, если OCR дал мало текста (чертёж/рисунок)."""
    from tmki_rag.retrieval import chunk_text_quality

    if not chunks:
        return "Текст документа не извлечён — возможно, это скан чертежа или схемы. Нужен layout-парсер (Docling) или vision-модель."
    good = sum(1 for c in chunks if chunk_text_quality(c.get("content_preview") or "") > 0.35)
    if good == 0 and len(chunks) > 0:
        return (
            "Распознан мало осмысленного текста — документ может содержать чертёж или рукописные пометки. "
            "Для «понимания» начерченного планируется vision-слой (Ollama llava / Docling)."
        )
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
