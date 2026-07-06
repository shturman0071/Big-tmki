from __future__ import annotations

import argparse
import json
import mimetypes
import os
import subprocess
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from tmki_demo.director_dashboard import build_director_dashboard
from tmki_demo.pto_dashboard import build_pto_dashboard
from tmki_demo.doc_voice import (
    get_session_snapshot,
    list_documents,
    open_document,
    preview_document_text,
    process_turn,
)
from tmki_demo.qa_lab import resolve_archive_file
from tmki_demo.qa import ask_regulations, resolve_document, resolve_llm_provider
from tmki_rag.corpus_policy import corpus_policy_snapshot, normalize_corpus_id

STATIC_DIR = Path(__file__).resolve().parent / "static"
ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import"
DEMO_ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "demo"
LAST_ASK_PATH = DEMO_ARTIFACTS_DIR / "last_ask.json"


def _static_file_response(path: Path) -> tuple[bytes, str] | None:
    try:
        resolved = path.resolve()
        if STATIC_DIR.resolve() not in resolved.parents and resolved != STATIC_DIR.resolve():
            return None
        if not resolved.is_file():
            return None
        data = resolved.read_bytes()
        mime, _ = mimetypes.guess_type(str(resolved))
        return data, mime or "application/octet-stream"
    except OSError:
        return None


class DemoHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


_status_cache: tuple[float, dict[str, Any]] | None = None


def _save_last_ask(question: str, corpus: str, result: dict[str, Any]) -> None:
    from datetime import datetime, timezone

    DEMO_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "question": question,
        "corpus": corpus,
        "answer": result.get("answer"),
        "citations": result.get("citations") or [],
        "search_debug": result.get("search_debug"),
        "meta": {
            "backend": result.get("backend"),
            "index_rows": result.get("index_rows"),
            "intent": result.get("intent"),
            "confidence": result.get("confidence"),
            "llm_provider": result.get("llm_provider"),
            "corpus_id": result.get("corpus_id"),
        },
    }
    LAST_ASK_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_last_ask() -> dict[str, Any] | None:
    if not LAST_ASK_PATH.is_file():
        return None
    try:
        return json.loads(LAST_ASK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _pgvector_corpus_counts() -> dict[str, int]:
    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        return {}
    try:
        import psycopg2

        conn = psycopg2.connect(dsn, connect_timeout=3)
        cur = conn.cursor()
        cur.execute(
            "SELECT corpus_id, COUNT(*) FROM chunks GROUP BY corpus_id ORDER BY COUNT(*) DESC"
        )
        rows = {str(r[0] or "null"): int(r[1]) for r in cur.fetchall()}
        cur.close()
        conn.close()
        return rows
    except Exception:
        return {}


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

    from tmki_voice.tts import tts_voice_catalog

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
        "tts": tts_voice_catalog(),
        "whisper_preset": os.environ.get("WHISPER_PRESET", "fast"),
        "stt_fix": stt_fix_selftest(),
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
        "index_chunks": _pgvector_corpus_counts(),
        "load_skru2_state": (
            json.loads((DEMO_ARTIFACTS_DIR / "load-skru2-state.json").read_text(encoding="utf-8"))
            if (DEMO_ARTIFACTS_DIR / "load-skru2-state.json").is_file()
            else None
        ),
        "load_vks_state": (
            json.loads((DEMO_ARTIFACTS_DIR / "load-vks-state.json").read_text(encoding="utf-8"))
            if (DEMO_ARTIFACTS_DIR / "load-vks-state.json").is_file()
            else None
        ),
    }
    state = ARTIFACTS_DIR / "reindex-state.json"
    if state.is_file():
        try:
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
                "raw_text": raw_text,
            }
            if text != raw_text and "+fix" not in (result.provider or ""):
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
        if parsed.path in ("/pto", "/pto.html"):
            html = (STATIC_DIR / "pto.html").read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        if parsed.path in ("/director", "/director.html"):
            html = (STATIC_DIR / "director.html").read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        if parsed.path in ("/voice-doc", "/voice-doc.html"):
            html = (STATIC_DIR / "voice-doc.html").read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        if parsed.path in ("/qa-lab", "/qa-lab.html", "/qa-lab/doc", "/qa-lab/question", "/qa-lab/verdict"):
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", "/voice-doc")
            self.end_headers()
            return
        if parsed.path == "/api/doc/raw":
            params = parse_qs(parsed.query)
            corpus = normalize_corpus_id((params.get("corpus") or ["skru-2"])[0])
            rel = (params.get("rel") or [None])[0]
            if not rel:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "rel required"})
                return
            target = resolve_archive_file(corpus_id=corpus, relative_path=rel)
            if not target:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "file not found"})
                return
            mime, _ = mimetypes.guess_type(str(target))
            try:
                data = target.read_bytes()
            except OSError as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if parsed.path == "/api/doc/preview":
            params = parse_qs(parsed.query)
            corpus = normalize_corpus_id((params.get("corpus") or ["skru-2"])[0])
            rel = (params.get("rel") or [None])[0]
            if not rel:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "rel required"})
                return
            try:
                self._send_json(
                    HTTPStatus.OK,
                    preview_document_text(corpus_id=corpus, relative_path=rel),
                )
            except FileNotFoundError:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "file not found"})
            except Exception as exc:  # noqa: BLE001
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return
        if parsed.path == "/api/voice-doc/docs":
            params = parse_qs(parsed.query)
            corpus = normalize_corpus_id((params.get("corpus") or ["skru-2"])[0])
            q = (params.get("q") or [""])[0]
            limit = int((params.get("limit") or ["40"])[0])
            self._send_json(HTTPStatus.OK, list_documents(corpus_id=corpus, query=q, limit=limit))
            return
        if parsed.path == "/api/voice-doc/state":
            params = parse_qs(parsed.query)
            sid = (params.get("session_id") or [""])[0]
            self._send_json(HTTPStatus.OK, get_session_snapshot(sid))
            return
        if parsed.path.startswith("/static/"):
            rel = parsed.path.removeprefix("/static/").lstrip("/")
            if rel and ".." not in rel:
                served = _static_file_response(STATIC_DIR / rel)
                if served:
                    data, mime = served
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
        if parsed.path == "/api/dashboard/director":
            counts = _pgvector_corpus_counts()
            self._send_json(HTTPStatus.OK, build_director_dashboard(index_stats=counts))
            return
        if parsed.path == "/api/dashboard/pto":
            counts = _pgvector_corpus_counts()
            self._send_json(HTTPStatus.OK, build_pto_dashboard(index_stats=counts))
            return
        if parsed.path == "/api/status":
            self._send_json(HTTPStatus.OK, _demo_status_snapshot())
            return
        if parsed.path == "/api/last-ask":
            data = _read_last_ask()
            if data is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "no last ask yet"})
            else:
                self._send_json(HTTPStatus.OK, data)
            return
        if parsed.path == "/api/doc/resolve":
            params = parse_qs(parsed.query)
            doc_id = (params.get("doc_id") or [None])[0]
            query = (params.get("q") or [None])[0]
            corpus = normalize_corpus_id((params.get("corpus") or [None])[0])
            self._send_json(HTTPStatus.OK, resolve_document(doc_id=doc_id, query=query, corpus_id=corpus))
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
                _save_last_ask(question, corpus, result)
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
        if self.path == "/api/tts/preview":
            try:
                from tmki_demo.doc_voice import synthesize_tts_payload

                body = self._read_json()
                text = (body.get("text") or "Проверка голоса.").strip()
                voice = (body.get("voice") or body.get("tts_voice") or "").strip() or None
                payload = synthesize_tts_payload(text[:200], voice_id=voice)
                self._send_json(HTTPStatus.OK, payload)
            except Exception as exc:  # noqa: BLE001
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return
        if self.path == "/api/voice-doc/open":
            try:
                body = self._read_json()
                snap = open_document(
                    corpus_id=normalize_corpus_id(body.get("corpus") or "skru-2"),
                    relative_path=str(body.get("relative_path") or ""),
                    session_id=(body.get("session_id") or None),
                    llm=(body.get("llm") or "ollama").lower(),
                    tts_voice=(body.get("tts_voice") or None),
                )
                self._send_json(HTTPStatus.OK, snap)
            except Exception as exc:  # noqa: BLE001
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return
        if self.path == "/api/voice-doc/turn":
            try:
                body = self._read_json()
                snap = process_turn(
                    session_id=str(body.get("session_id") or ""),
                    kind=str(body.get("kind") or "user_question"),
                    text=str(body.get("text") or ""),
                    raw_text=(body.get("raw_text") or None),
                    llm=(body.get("llm") or None),
                    tts_voice=(body.get("tts_voice") or None),
                )
                self._send_json(HTTPStatus.OK, snap)
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return
        if self.path.startswith("/api/qa-lab/"):
            self._send_json(HTTPStatus.GONE, {"error": "removed; use /voice-doc"})
            return
        if self.path == "/api/eval/qa/run":
            self._send_json(HTTPStatus.GONE, {"error": "removed; use /voice-doc"})
            return
        if self.path == "/api/eval/qa/reset":
            self._send_json(HTTPStatus.GONE, {"error": "removed; use /voice-doc"})
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


def _warmup_silero() -> None:
    try:
        from tmki_voice.silero_tts import preload_silero_model

        model_id = preload_silero_model()
        print(f"  Warmup: Silero ready ({model_id})", flush=True)  # noqa: T201
    except Exception as exc:  # noqa: BLE001
        print(f"  Silero warmup skipped: {exc}", flush=True)  # noqa: T201


def _warmup_audio() -> None:
    if os.environ.get("TMKI_TTS_PROVIDER", "stub").lower() == "silero":
        _warmup_silero()
    if os.environ.get("TMKI_STT_PROVIDER", "stub").lower() == "whisper":
        _warmup_whisper()


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


def serve(host: str = "127.0.0.1", port: int = 8770) -> None:
    server = DemoHTTPServer((host, port), DemoHandler)
    url = f"http://{host}:{port}/"
    print(f"TMKI Demo UI: {url}", flush=True)  # noqa: T201
    print(f"  LLM: {_startup_llm_status()}", flush=True)  # noqa: T201
    if os.environ.get("TMKI_DEMO_OPEN_BROWSER", "").lower() in ("1", "true", "yes"):
        open_path = os.environ.get("TMKI_DEMO_OPEN_PATH", "/")
        if not open_path.startswith("/"):
            open_path = "/" + open_path
        threading.Thread(
            target=_open_browser,
            args=(f"http://{host}:{port}{open_path}",),
            name="tmki-demo-browser",
            daemon=True,
        ).start()
    threading.Thread(target=_warmup_audio, name="tmki-audio-warmup", daemon=True).start()
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
