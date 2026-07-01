from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from tmki_admin.grants_service import GrantServiceError, open_grant_service

ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"


class GrantsHandler(BaseHTTPRequestHandler):
    service: GrantService
    root: Path

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

    def _granter(self, body: dict[str, Any]) -> dict[str, Any]:
        granter = body.get("granter") or {}
        required = ("employee_id", "project_role", "department_id", "company_id", "project_id")
        if not all(granter.get(k) for k in required):
            raise GrantServiceError("granter: нужны employee_id, project_role, department_id, company_id, project_id")
        granter.setdefault("clearance", "restricted")
        granter.setdefault("env", "development")
        return granter

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

        qs = parse_qs(parsed.query)
        if parsed.path == "/api/folders":
            dept = qs.get("department_id", [""])[0]
            folders = self.service.folders_for_department(dept) if dept else self.service.folders
            self._send_json(HTTPStatus.OK, {"folders": folders})
            return

        if parsed.path == "/api/grants":
            employee_id = qs.get("employee_id", [""])[0]
            if not employee_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "employee_id required"})
                return
            grants = self.service.store.active_for_employee(employee_id)
            self._send_json(HTTPStatus.OK, {"grants": grants})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/grants/toggle":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            body = self._read_json()
            granter = self._granter(body)
            employee_id = body["employee_id"]
            folder_id = body["folder_id"]
            mode = body["mode"]

            if mode == "deny_read":
                entry = self.service.set_deny_read(
                    granter,
                    employee_id=employee_id,
                    folder_id=folder_id,
                    reason=body.get("reason", ""),
                )
            elif mode == "grant_read":
                entry = self.service.set_grant(
                    granter,
                    employee_id=employee_id,
                    folder_id=folder_id,
                    actions=["read"],
                    valid_to=body.get("valid_to"),
                    reason=body.get("reason", ""),
                )
            elif mode == "grant_write":
                entry = self.service.set_grant(
                    granter,
                    employee_id=employee_id,
                    folder_id=folder_id,
                    actions=["read", "write"],
                    valid_to=body.get("valid_to"),
                    reason=body.get("reason", ""),
                )
            elif mode == "revoke":
                grant_type = body.get("grant_type", "grant")
                ok = self.service.revoke(
                    granter,
                    employee_id=employee_id,
                    folder_id=folder_id,
                    grant_type=grant_type,
                )
                self._send_json(HTTPStatus.OK, {"revoked": ok})
                return
            else:
                raise GrantServiceError(f"Неизвестный mode: {mode}")

            # SharePoint sync (stub) после изменения
            from tmki_sharepoint import StubSharePointAdapter, build_sync_plan

            plan = build_sync_plan(self.service.store.grants, self.service.folders)
            adapter = StubSharePointAdapter()
            sync_result = adapter.apply(plan)

            self._send_json(
                HTTPStatus.OK,
                {"grant": entry, "sharepoint_sync": sync_result},
            )
        except GrantServiceError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except (KeyError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})


def serve(host: str = "127.0.0.1", port: int = 8765, root: Path | None = None) -> None:
    root = root or ROOT
    service = open_grant_service(root)

    handler = GrantsHandler
    handler.service = service  # type: ignore[attr-defined]
    handler.root = root  # type: ignore[attr-defined]

    server = ThreadingHTTPServer((host, port), handler)
    print(f"TMKI Admin UI: http://{host}:{port}/")  # noqa: T201
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="TMKI folder grants admin UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    serve(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
