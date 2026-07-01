#!/usr/bin/env python3
"""Проверка доступности HTTP OCR endpoints (MinerU / Mistral)."""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request


def _probe(name: str, url: str, timeout: float) -> bool:
    if not url:
        print(f"  [skip] {name}: URL не задан")
        return True
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "tmki-health/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            print(f"  [ok] {name}: HTTP {resp.status} {url}")
            return True
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403, 405, 422}:
            print(f"  [ok] {name}: HTTP {exc.code} (endpoint доступен) {url}")
            return True
        print(f"  [fail] {name}: HTTP {exc.code} {url}")
        return False
    except Exception as exc:
        print(f"  [fail] {name}: {exc} ({url})")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe MinerU/Mistral OCR HTTP endpoints")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    print("TMKI HTTP OCR probe\n")
    ok = True
    ok &= _probe("MINERU_API_URL", os.environ.get("MINERU_API_URL", ""), args.timeout)
    ok &= _probe("MISTRAL_OCR_API_URL", os.environ.get("MISTRAL_OCR_API_URL", ""), args.timeout)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
