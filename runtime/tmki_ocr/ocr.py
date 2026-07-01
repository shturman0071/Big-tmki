from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

MINERU_PARSER_VERSION = "mineru@2.1.0"
MISTRAL_PARSER_VERSION = "mistral-ocr-4@2026-06"
CONFIDENCE_THRESHOLD = 0.65
EMPTY_TEXT_THRESHOLD = 50


@dataclass
class OcrAttempt:
    provider: str
    status: str
    duration_ms: int
    text: str
    page_count: int
    avg_confidence: float
    error_code: str | None = None


class OcrProvider(Protocol):
    name: str
    parser_version: str

    def extract(self, raw_bytes: bytes) -> OcrAttempt: ...


class StubMinerUProvider:
    name = "mineru"
    parser_version = MINERU_PARSER_VERSION

    def __init__(self, *, mode: str = "ok") -> None:
        self._mode = mode

    def extract(self, raw_bytes: bytes) -> OcrAttempt:
        if self._mode == "error":
            return OcrAttempt(
                provider=self.name,
                status="failed",
                duration_ms=10,
                text="",
                page_count=0,
                avg_confidence=0.0,
                error_code="MINERU_API_ERROR",
            )
        if self._mode == "low_confidence":
            return OcrAttempt(
                provider=self.name,
                status="completed",
                duration_ms=20,
                text="короткий текст",
                page_count=2,
                avg_confidence=0.4,
            )
        if self._mode == "empty":
            return OcrAttempt(
                provider=self.name,
                status="completed",
                duration_ms=15,
                text="",
                page_count=2,
                avg_confidence=0.9,
            )
        text = _mock_text_from_bytes(raw_bytes)
        return OcrAttempt(
            provider=self.name,
            status="completed",
            duration_ms=25,
            text=text,
            page_count=1,
            avg_confidence=0.92,
        )


class StubMistralOcrProvider:
    name = "mistral_ocr_4"
    parser_version = MISTRAL_PARSER_VERSION

    def extract(self, raw_bytes: bytes) -> OcrAttempt:
        text = _mock_text_from_bytes(raw_bytes) or "Fallback OCR: извлечённый текст документа."
        return OcrAttempt(
            provider=self.name,
            status="completed",
            duration_ms=40,
            text=text,
            page_count=1,
            avg_confidence=0.88,
        )


def _mock_text_from_bytes(raw_bytes: bytes) -> str:
    if raw_bytes.startswith(b"%PDF"):
        return "Маркшейдерская съёмка: извлечённый текст из PDF (stub MinerU/Mistral)."
    if raw_bytes.startswith(b"FORCE_OCR_FALLBACK"):
        return "Маркшейдерская съёмка: fallback OCR текст."
    try:
        decoded = raw_bytes.decode("utf-8")
        if decoded.strip():
            return decoded
    except UnicodeDecodeError:
        pass
    return "Документ TMKI: stub OCR content."


def _needs_fallback(primary: OcrAttempt) -> str | None:
    if primary.status == "failed":
        return "primary_error"
    if primary.avg_confidence < CONFIDENCE_THRESHOLD:
        return "low_confidence"
    if primary.page_count > 1 and len(primary.text) < EMPTY_TEXT_THRESHOLD:
        return "empty_text"
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_ocr(
    *,
    doc_id: str,
    trace_id: str,
    raw_bytes: bytes,
    mineru_mode: str = "ok",
) -> dict[str, Any]:
    """
    OCR pipeline: MinerU → Mistral fallback (stub, 09_document_processing.md).
    Контракт: schemas/document/ocr-result.schema.json
    """
    started = datetime.now(timezone.utc)
    primary = StubMinerUProvider(mode=mineru_mode).extract(raw_bytes)
    fallback_reason = _needs_fallback(primary)
    fallback_used = False
    provider_used = "mineru"
    parser_version = MINERU_PARSER_VERSION
    final = primary
    warnings: list[str] = []
    errors: list[str] = []

    primary_attempt = {
        "provider": "mineru",
        "status": primary.status,
        "duration_ms": primary.duration_ms,
    }
    if primary.error_code:
        primary_attempt["error_code"] = primary.error_code

    if fallback_reason:
        fallback_used = True
        mistral = StubMistralOcrProvider().extract(raw_bytes)
        final = mistral
        provider_used = "mistral_ocr_4"
        parser_version = MISTRAL_PARSER_VERSION
        warnings.append(f"fallback:{fallback_reason}")

    ocr_status = "completed" if final.status == "completed" and final.text else "failed"
    if ocr_status == "failed":
        errors.append("OCR extraction failed")

    duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)

    return {
        "schema_version": "0.1",
        "doc_id": doc_id,
        "trace_id": trace_id,
        "ocr_status": ocr_status,
        "provider_used": provider_used,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason or "none",
        "primary_attempt": primary_attempt,
        "parser_version": parser_version,
        "page_count": final.page_count,
        "extracted_char_count": len(final.text),
        "avg_confidence": final.avg_confidence,
        "pages": [
            {
                "page": 1,
                "char_count": len(final.text),
                "confidence": final.avg_confidence,
            }
        ],
        "markdown_path": f"artifacts/{doc_id}/markdown.md",
        "assets_count": 0,
        "warnings": warnings,
        "errors": errors,
        "duration_ms": duration_ms,
        "occurred_at": _now_iso(),
        "_markdown": final.text,
    }
