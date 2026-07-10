"""Test login directly on Kanboard port 8790 (no proxy)."""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

BASE = "http://127.0.0.1:8790"


def main() -> int:
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    login_page = opener.open(f"{BASE}/?controller=AuthController&action=login", timeout=10).read().decode()
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', login_page)
    body = urllib.parse.urlencode(
        {
            "username": "admin",
            "password": "admin",
            "remember_me": "1",
            "csrf_token": csrf.group(1) if csrf else "",
        }
    ).encode()
    req = urllib.request.Request(
        f"{BASE}/?controller=AuthController&action=check",
        data=body,
        method="POST",
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    html = opener.open(req, timeout=10).read().decode("utf-8", "ignore")
    print("direct_bad", "Bad username" in html)
    print("direct_board", "task-board" in html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
