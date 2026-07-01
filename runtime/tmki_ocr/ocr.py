from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

MINERU_PARSER_VERSION = "mineru@2.1.0"
MISTRAL_PARSER_VERSION = "mistral-ocr-4@2026-06"
CONFIDENCE_THRESHOLD = 0.65
EMPTY_TEXT_THRESHOLD = 50

HttpPostFn = Callable[[str, dict[str, Any], dict[str, str], int], dict[str, Any]]


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


def _default_http_post(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OCR HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OCR HTTP unavailable: {exc.reason}") from exc


def _http_post_with_retry(
    http_post: HttpPostFn,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int,
    *,
    retries: int | None = None,
) -> dict[str, Any]:
    max_retries = retries if retries is not None else int(os.environ.get("TMKI_OCR_HTTP_RETRIES", "1"))
    delay_ms = int(os.environ.get("TMKI_OCR_HTTP_RETRY_DELAY_MS", "500"))
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return http_post(url, payload, headers, timeout)
        except Exception as exc:  # noqa: BLE001 — retry OCR HTTP
            last_exc = exc
            if attempt >= max_retries:
                raise
            if delay_ms > 0:
                time.sleep((delay_ms / 1000.0) * (attempt + 1))
    if last_exc:
        raise last_exc
    return {}


from tmki_ocr.extractors import extract_local_text, guess_suffix


class LocalMinerUProvider:
    """Локальное извлечение текста (txt/docx/pdf+pypdf) без внешнего API."""

    name = "mineru"
    parser_version = "local-text@1.0"

    def __init__(self, *, source_name: str | None = None) -> None:
        self._source_name = source_name

    def extract(self, raw_bytes: bytes) -> OcrAttempt:
        started = datetime.now(timezone.utc)
        suffix = guess_suffix(raw_bytes, self._source_name)
        result = extract_local_text(raw_bytes, suffix=suffix)
        text = result["text"]
        page_count = int(result["page_count"] or 1)
        confidence = float(result["confidence"])
        status = "completed" if text else "failed"
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return OcrAttempt(
            provider=self.name,
            status=status,
            duration_ms=duration_ms,
            text=text,
            page_count=page_count,
            avg_confidence=confidence,
            error_code=None if status == "completed" else "LOCAL_EXTRACT_EMPTY",
        )


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


class HttpMinerUProvider:
    name = "mineru"
    parser_version = MINERU_PARSER_VERSION

    def __init__(
        self,
        *,
        api_url: str | None = None,
        api_key: str | None = None,
        http_post: HttpPostFn | None = None,
        timeout: int = 120,
    ) -> None:
        self._api_url = api_url or os.environ.get("MINERU_API_URL", "")
        self._api_key = api_key or os.environ.get("MINERU_API_KEY", "")
        self._http_post = http_post or _default_http_post
        self._timeout = timeout

    def extract(self, raw_bytes: bytes) -> OcrAttempt:
        if not self._api_url:
            raise RuntimeError("MINERU_API_URL не задан для TMKI_OCR_MODE=http")
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = {
            "file_base64": base64.b64encode(raw_bytes).decode("ascii"),
            "output_format": "markdown",
        }
        started = datetime.now(timezone.utc)
        data = _http_post_with_retry(self._http_post, self._api_url, payload, headers, self._timeout)
        text = data.get("markdown") or data.get("text") or ""
        page_count = int(data.get("page_count") or len(data.get("pages", [])) or 1)
        confidence = float(data.get("avg_confidence", 0.85))
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        status = "completed" if text else "failed"
        return OcrAttempt(
            provider=self.name,
            status=status,
            duration_ms=duration_ms,
            text=text,
            page_count=page_count,
            avg_confidence=confidence,
            error_code=None if status == "completed" else "MINERU_API_ERROR",
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


class HttpMistralOcrProvider:
    name = "mistral_ocr_4"
    parser_version = MISTRAL_PARSER_VERSION

    def __init__(
        self,
        *,
        api_url: str | None = None,
        api_key: str | None = None,
        http_post: HttpPostFn | None = None,
        timeout: int = 120,
    ) -> None:
        self._api_url = api_url or os.environ.get("MISTRAL_OCR_API_URL", "")
        self._api_key = api_key or os.environ.get("MISTRAL_API_KEY", "")
        self._http_post = http_post or _default_http_post
        self._timeout = timeout

    def extract(self, raw_bytes: bytes) -> OcrAttempt:
        if not self._api_url:
            raise RuntimeError("MISTRAL_OCR_API_URL не задан для TMKI_OCR_MODE=http")
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = {
            "document": {
                "type": "base64",
                "content": base64.b64encode(raw_bytes).decode("ascii"),
            }
        }
        started = datetime.now(timezone.utc)
        data = _http_post_with_retry(self._http_post, self._api_url, payload, headers, self._timeout)
        pages = data.get("pages") or []
        text = data.get("markdown") or "\n".join(p.get("text", "") for p in pages)
        page_count = int(data.get("page_count") or len(pages) or 1)
        confidence = float(data.get("avg_confidence", 0.88))
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return OcrAttempt(
            provider=self.name,
            status="completed" if text else "failed",
            duration_ms=duration_ms,
            text=text,
            page_count=page_count,
            avg_confidence=confidence,
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


def get_mineru_provider(*, mode: str = "ok", source_name: str | None = None) -> OcrProvider:
    ocr_mode = os.environ.get("TMKI_OCR_MODE", "stub").lower()
    if ocr_mode == "http":
        return HttpMinerUProvider()
    if ocr_mode == "local":
        return LocalMinerUProvider(source_name=source_name)
    return StubMinerUProvider(mode=mode)


def get_mistral_provider() -> OcrProvider:
    if os.environ.get("TMKI_OCR_MODE", "stub").lower() == "http":
        return HttpMistralOcrProvider()
    return StubMistralOcrProvider()


def run_ocr(
    *,
    doc_id: str,
    trace_id: str,
    raw_bytes: bytes,
    mineru_mode: str = "ok",
    mineru_provider: OcrProvider | None = None,
    mistral_provider: OcrProvider | None = None,
    source_name: str | None = None,
) -> dict[str, Any]:
    """
    OCR pipeline: MinerU → Mistral fallback.
    TMKI_OCR_MODE=stub|local|http (default stub).
    source_name — имя файла для local extractor (.docx/.pdf/...).
    """
    started = datetime.now(timezone.utc)
    primary = (mineru_provider or get_mineru_provider(mode=mineru_mode, source_name=source_name)).extract(raw_bytes)
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
        mistral = (mistral_provider or get_mistral_provider()).extract(raw_bytes)
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
