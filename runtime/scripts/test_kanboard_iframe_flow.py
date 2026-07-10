"""Bootstrap + load board through proxy."""
from __future__ import annotations

import http.cookiejar
import json
import re
import urllib.request

BASE = "http://127.0.0.1:8770"


def main() -> int:
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    bootstrap = urllib.request.Request(
        f"{BASE}/api/kanboard/bootstrap",
        data=b"{}",
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    opener.open(bootstrap, timeout=15).read()
    html = opener.open(
        f"{BASE}/kanboard/?controller=BoardViewController&action=show&project_id=1",
        timeout=15,
    ).read().decode("utf-8", "ignore")
    print("login_form", 'name="password"' in html)
    print("board", "task-board" in html or "Сатимол" in html)
    print("title", re.search(r"<title>([^<]+)", html, re.I).group(1).strip() if re.search(r"<title>", html, re.I) else "?")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
