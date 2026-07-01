from __future__ import annotations

import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

_lock = threading.Lock()
_server: HTTPServer | None = None
_content: str = "<html><body>TMKI cast</body></html>"


def _local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


class _CastHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = _content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def publish_cast_html(html: str, *, host: str = "0.0.0.0", port: int = 8766) -> str:
    """Обновить HTML и вернуть URL для открытия на TV/планшете в той же сети."""
    global _content, _server
    _content = html
    with _lock:
        if _server is None:
            _server = HTTPServer((host, port), _CastHandler)
            threading.Thread(target=_server.serve_forever, daemon=True).start()
    display_host = _local_ip() if host in {"0.0.0.0", ""} else host
    return f"http://{display_host}:{port}/"


def reset_cast_server() -> None:
    """Остановить сервер (для тестов)."""
    global _server
    with _lock:
        if _server is not None:
            _server.shutdown()
            _server.server_close()
            _server = None
