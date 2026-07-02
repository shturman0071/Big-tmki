from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from tmki_demo.qa import ask_regulations, pipeline_status_snapshot, resolve_document, resolve_llm_provider

STATIC_DIR = Path(__file__).resolve().parent / "static"


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
            status = pipeline_status_snapshot()
            ops = status.get("ops") or {}
            report = ops.get("report") or {}
            self._send_json(
                HTTPStatus.OK,
                {
                    "phase": status.get("phase"),
                    "progress": report.get("live_progress"),
                    "total": report.get("total"),
                    "percent": report.get("percent"),
                    "finalize_done": ops.get("finalize_done"),
                    "docker": (status.get("docker") or {}).get("ready"),
                    "llm": resolve_llm_provider(),
                },
            )
            return
        if parsed.path == "/api/doc/resolve":
            params = parse_qs(parsed.query)
            doc_id = (params.get("doc_id") or [None])[0]
            query = (params.get("q") or [None])[0]
            self._send_json(HTTPStatus.OK, resolve_document(doc_id=doc_id, query=query))
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
                result = ask_regulations(question, llm_provider=llm)
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


def serve(host: str = "127.0.0.1", port: int = 8767) -> None:
    server = ThreadingHTTPServer((host, port), DemoHandler)
    print(f"TMKI Demo UI: http://{host}:{port}/")  # noqa: T201
    print(f"  LLM: {resolve_llm_provider()}")  # noqa: T201
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="TMKI regulations demo UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    serve(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
