from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable

HttpRequestFn = Callable[[str, str, dict[str, Any] | None, dict[str, str]], dict[str, Any]]


def default_http_request(
    method: str,
    url: str,
    body: dict[str, Any] | None,
    headers: dict[str, str],
) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            return {"status_code": resp.status, "body": parsed}
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err) if err else {}
        except json.JSONDecodeError:
            parsed = {"error": err}
        return {"status_code": exc.code, "body": parsed, "error": True}
