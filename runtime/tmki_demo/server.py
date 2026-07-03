from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from tmki_demo.qa import (
    analyze_document,
    ask_regulations,
    chat_message,
    get_chat_session,
    resolve_document,
    resolve_llm_provider,
)
from tmki_rag.corpus_policy import corpus_policy_snapshot, normalize_corpus_id

STATIC_DIR = Path(__file__).resolve().parent / "static"
ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import"


class DemoHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


_status_cache: tuple[float, dict[str, Any]] | None = None


def _demo_status_snapshot() -> dict[str, Any]:
    """Лёгкий статус для UI (без docker/reindex-state на каждый запрос)."""
    global _status_cache
    import time

    now = time.time()
    if _status_cache and now - _status_cache[0] < 20:
        return _status_cache[1]

    from tmki_voice.stt_corrections import stt_fix_selftest
    from tmki_rag.cross_encoder import available as ce_available
    from tmki_rag.feature_flags import (
        cross_encoder_rerank_enabled,
        incremental_ingest_enabled,
        ingest_parser_backend,
        pgvector_backend_enabled,
        rag_fusion_enabled,
    )

    from tmki_ocr.parser_backend import resolve_parser_backend

    docling_ok = False
    try:
        import docling  # noqa: F401

        docling_ok = True
    except ImportError:
        pass

    payload: dict[str, Any] = {
        "phase": "demo",
        "progress": None,
        "total": None,
        "percent": None,
        "finalize_done": (ARTIFACTS_DIR / "finalize-done.json").is_file(),
        "docker": True,
        "llm": resolve_llm_provider(),
        "corpora": corpus_policy_snapshot(),
        "stt": os.environ.get("TMKI_STT_PROVIDER", "stub").lower(),
        "whisper_preset": os.environ.get("WHISPER_PRESET", "fast"),
        "stt_fix": stt_fix_selftest(),
        "chat": {
            "enabled": os.environ.get("TMKI_CHAT_MODE", "1").lower() not in ("0", "false", "no"),
            "persist": os.environ.get("TMKI_CHAT_PERSIST", "1").lower() not in ("0", "false", "no"),
        },
        "retrieval": {
            "rag_fusion": rag_fusion_enabled(),
            "cross_encoder_rerank": cross_encoder_rerank_enabled(),
            "cross_encoder_installed": ce_available(),
            "incremental_ingest": incremental_ingest_enabled(),
            "ingest_parser": ingest_parser_backend(),
            "ingest_parser_resolved": resolve_parser_backend(),
            "docling_installed": docling_ok,
            "pgvector_ready": pgvector_backend_enabled(),
        },
    }
    state = ARTIFACTS_DIR / "reindex-state.json"
    if state.is_file():
        try:
            import json

            data = json.loads(state.read_text(encoding="utf-8"))
            total = int(data.get("total_candidates") or 0)
            processed = len(data.get("processed") or [])
            if total:
                payload["progress"] = processed
                payload["total"] = total
                payload["percent"] = round(100.0 * processed / total, 1)
                payload["phase"] = "post_finalize" if payload["finalize_done"] else "reindexing"
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    _status_cache = (now, payload)
    return payload


class DemoHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length else b""

    def _handle_transcribe(self) -> None:
        import tempfile

        from tmki_voice.stt import FasterWhisperSttProvider, get_stt_provider
        from tmki_voice.stt_corrections import apply_stt_corrections

        preset = (self.headers.get("X-Whisper-Preset") or "").strip().lower()
        test_mode = (self.headers.get("X-Whisper-Test") or "").lower() in ("1", "true", "yes")
        if test_mode and preset in {"quality", "balanced", "fast", "voice"}:
            provider = FasterWhisperSttProvider(preset=preset)
        else:
            provider = get_stt_provider()
        if type(provider).__name__ == "StubSttProvider":
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "error": "STT не настроен",
                    "hint": "Установите TMKI_STT_PROVIDER=whisper и pip install -e \".[stt]\"",
                },
            )
            return

        audio = self._read_body()
        if not audio:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "empty audio"})
            return

        content_type = (self.headers.get("Content-Type") or "").lower()
        suffix = ".webm"
        if "ogg" in content_type:
            suffix = ".ogg"
        elif "wav" in content_type:
            suffix = ".wav"
        elif "mp4" in content_type or "m4a" in content_type:
            suffix = ".m4a"
        elif "mpeg" in content_type or "mp3" in content_type:
            suffix = ".mp3"

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio)
                tmp_path = tmp.name
            result = provider.transcribe(tmp_path)
            raw_text = result.raw_text or result.text
            text = apply_stt_corrections(raw_text)
            payload = {
                "text": text,
                "provider": result.provider,
                "language": result.language,
            }
            if text != raw_text:
                payload["raw_text"] = raw_text
                if "+fix" not in (result.provider or ""):
                    payload["provider"] = (result.provider or "whisper") + "+fix"
            self._send_json(HTTPStatus.OK, payload)
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            html = (STATIC_DIR / "index.html").read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        if parsed.path == "/api/status":
            self._send_json(HTTPStatus.OK, _demo_status_snapshot())
            return
        if parsed.path == "/api/doc/resolve":
            params = parse_qs(parsed.query)
            doc_id = (params.get("doc_id") or [None])[0]
            query = (params.get("q") or [None])[0]
            corpus = normalize_corpus_id((params.get("corpus") or [None])[0])
            self._send_json(HTTPStatus.OK, resolve_document(doc_id=doc_id, query=query, corpus_id=corpus))
            return
        if parsed.path == "/api/session":
            params = parse_qs(parsed.query)
            sid = (params.get("session_id") or [None])[0]
            if not sid:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "session_id required"})
                return
            self._send_json(HTTPStatus.OK, get_chat_session(sid))
            return
        if parsed.path == "/api/trainer":
            params = parse_qs(parsed.query)
            user = (params.get("user") or ["default"])[0] or "default"
            from tmki_trainer import trainer_snapshot

            self._send_json(HTTPStatus.OK, trainer_snapshot(user))
            return
        if parsed.path == "/api/doc/profile":
            params = parse_qs(parsed.query)
            doc_id = (params.get("doc_id") or [None])[0]
            corpus = normalize_corpus_id((params.get("corpus") or [None])[0])
            if not doc_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "doc_id required"})
                return
            from tmki_demo.qa import _get_memory_store

            store = _get_memory_store(corpus_id=corpus)
            profile = store.get(doc_id)
            if profile:
                self._send_json(HTTPStatus.OK, {"status": "ok", "profile": profile.to_dict()})
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found", "doc_id": doc_id})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/trainer/attempt":
            try:
                body = self._read_json()
                lesson_id = (body.get("lesson_id") or "").strip()
                user_answer = (body.get("answer") or "").strip()
                user_id = (body.get("user_id") or "default").strip() or "default"
                if not lesson_id or not user_answer:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "lesson_id and answer required"})
                    return
                from tmki_trainer import evaluate_attempt, load_curriculum, record_attempt

                curriculum = load_curriculum()
                lesson = curriculum.lesson_by_id(lesson_id)
                if not lesson:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "lesson not found"})
                    return
                result = evaluate_attempt(lesson, user_answer)
                progress = record_attempt(user_id, lesson_id, result)
                self._send_json(
                    HTTPStatus.OK,
                    {"result": result.to_dict(), "progress": progress.get("completed", [])},
                )
            except Exception as exc:  # noqa: BLE001
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return
        if self.path == "/api/trainer/practice":
            try:
                body = self._read_json()
                lesson_id = (body.get("lesson_id") or "").strip()
                session_id = (body.get("session_id") or "").strip() or None
                follow_up = bool(body.get("follow_up"))
                if not lesson_id:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "lesson_id required"})
                    return
                from tmki_trainer.engine import load_curriculum, run_system_practice

                curriculum = load_curriculum()
                lesson = curriculum.lesson_by_id(lesson_id)
                if not lesson:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "lesson not found"})
                    return
                out = run_system_practice(lesson, session_id=session_id, follow_up=follow_up)
                self._send_json(HTTPStatus.OK, out)
            except Exception as exc:  # noqa: BLE001
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return
        if self.path == "/api/chat":
            try:
                body = self._read_json()
                message = (body.get("message") or body.get("question") or "").strip()
                if not message:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "message required"})
                    return
                llm = body.get("llm")
                corpus = normalize_corpus_id(body.get("corpus"))
                session_id = (body.get("session_id") or "").strip() or None
                result = chat_message(
                    message,
                    session_id=session_id,
                    llm_provider=llm,
                    corpus_id=corpus,
                )
                if result.get("error"):
                    self._send_json(HTTPStatus.BAD_REQUEST, result)
                    return
                self._send_json(HTTPStatus.OK, result)
            except Exception as exc:  # noqa: BLE001 — demo boundary
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return
        if self.path == "/api/ask":
            try:
                body = self._read_json()
                question = (body.get("question") or "").strip()
                if not question:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "question required"})
                    return
                llm = body.get("llm")
                corpus = normalize_corpus_id(body.get("corpus"))
                result = ask_regulations(question, llm_provider=llm, corpus_id=corpus)
                self._send_json(HTTPStatus.OK, result)
            except Exception as exc:  # noqa: BLE001 — demo boundary
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return
        if self.path == "/api/transcribe":
            try:
                self._handle_transcribe()
            except Exception as exc:  # noqa: BLE001 — demo boundary
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return
        if self.path == "/api/analyze":
            try:
                body = self._read_json()
                message = (body.get("question") or body.get("message") or "").strip()
                doc_id = (body.get("doc_id") or "").strip() or None
                rel = (body.get("relative_path") or "").strip() or None
                if not message and not doc_id and not rel:
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "question, doc_id or relative_path required"},
                    )
                    return
                llm = body.get("llm")
                corpus = normalize_corpus_id(body.get("corpus"))
                force = bool(body.get("force"))
                result = analyze_document(
                    message or "анализ документа",
                    doc_id=doc_id,
                    relative_path=rel,
                    llm_provider=llm,
                    corpus_id=corpus,
                    force=force,
                )
                self._send_json(HTTPStatus.OK, result)
            except Exception as exc:  # noqa: BLE001 — demo boundary
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return
        if self.path == "/api/doc/open":
            try:
                body = self._read_json()
                path = (body.get("absolute_path") or body.get("path") or "").strip()
                if not path:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "path required"})
                    return
                opened = _open_local_file(path)
                self._send_json(HTTPStatus.OK, opened)
            except Exception as exc:  # noqa: BLE001 — demo boundary
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})


def _open_local_file(path: str) -> dict[str, Any]:
    target = Path(path).resolve()
    if not target.is_file():
        return {"status": "not_found", "path": str(target)}
    if sys.platform == "win32":
        os.startfile(str(target))  # noqa: S606 — demo: open in default app
        return {"status": "opened", "path": str(target), "method": "os.startfile"}
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # noqa: S603
    return {"status": "opened", "path": str(target), "method": opener}


def _warmup_whisper() -> None:
    try:
        from tmki_voice.stt import preload_whisper_model

        preset = preload_whisper_model()
        print(f"  Warmup: Whisper ready ({preset})", flush=True)  # noqa: T201
    except Exception as exc:  # noqa: BLE001
        print(f"  Whisper warmup skipped: {exc}", flush=True)  # noqa: T201


def _warmup_demo() -> None:
    """Прогрев индекса при старте — первый вопрос в UI не ждёт минуты."""
    try:
        ask_regulations("промбезопасность", llm_provider="stub", hybrid=True)
        print("  Warmup: index ready", flush=True)  # noqa: T201
    except Exception as exc:  # noqa: BLE001
        print(f"  Warmup skipped: {exc}", flush=True)  # noqa: T201


def _startup_llm_status() -> str:
    configured = os.environ.get("TMKI_LLM_PROVIDER", "stub").lower()
    skru = resolve_llm_provider(corpus_id="skru-2")
    arm = resolve_llm_provider(corpus_id="arm-ks")
    return f"{configured} (СКРУ-2: {skru}, Армировка КС: {arm})"


def serve(host: str = "127.0.0.1", port: int = 8767) -> None:
    server = DemoHTTPServer((host, port), DemoHandler)
    url = f"http://{host}:{port}/"
    print(f"TMKI Demo UI: {url}", flush=True)  # noqa: T201
    print(f"  LLM: {_startup_llm_status()}", flush=True)  # noqa: T201
    if os.environ.get("TMKI_DEMO_OPEN_BROWSER", "").lower() in ("1", "true", "yes"):
        threading.Thread(target=_open_browser, args=(url,), name="tmki-demo-browser", daemon=True).start()
    if os.environ.get("TMKI_STT_PROVIDER", "stub").lower() == "whisper":
        threading.Thread(target=_warmup_whisper, name="tmki-whisper-warmup", daemon=True).start()
    if os.environ.get("TMKI_DEMO_WARMUP", "").lower() in ("1", "true", "yes"):
        threading.Thread(target=_warmup_demo, name="tmki-demo-warmup", daemon=True).start()
    server.serve_forever()


def _open_browser(url: str) -> None:
    import webbrowser

    webbrowser.open(url)
    print(f"  Browser: {url}", flush=True)  # noqa: T201


def main() -> None:
    parser = argparse.ArgumentParser(description="TMKI regulations demo UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args()
    serve(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
