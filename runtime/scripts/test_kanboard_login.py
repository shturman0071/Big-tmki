"""Проверка входа Kanboard через прокси демо."""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

BASE = "http://127.0.0.1:8770/kanboard"


def main() -> int:
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    login_page = opener.open(f"{BASE}/?controller=AuthController&action=login", timeout=10).read().decode()
    form = re.search(r'<form method="post" action="([^"]+)"', login_page)
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', login_page)
    print("form_action", form.group(1) if form else "MISSING")
    print("csrf", bool(csrf), "cookies_after_get", len(cj))
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
    resp = opener.open(req, timeout=10)
    html = resp.read().decode("utf-8", "ignore")
    print("status", resp.status, "url", resp.geturl())
    print("bad_login", "Bad username" in html or "bad username" in html.lower())
    print("has_board", "task-board" in html)
    print("still_login", 'name="password"' in html)
    print("task_board_on_login_page", "task-board" in login_page)
    for c in cj:
        print("cookie", c.name, "path=", c.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
