#!/usr/bin/env python3
"""Демо HTTP cast: открыть ответ MVP на TV/планшете в браузере по LAN URL."""

from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="TMKI display HTTP cast demo")
    parser.add_argument("message", nargs="?", default=None)
    parser.add_argument("--target", default="tv", choices=["tv", "tablet", "computer"])
    args = parser.parse_args()

    from tmki_runtime.cli_encoding import resolve_cli_message

    message = resolve_cli_message(positional=args.message, default="промбезопасность кран")
    os.environ.setdefault("TMKI_DISPLAY_PROVIDER", "http_cast")

    from tmki_voice.display import cast_mvp_output

    result = cast_mvp_output({"answer": message}, target=args.target)
    print(f"target={result.target} method={result.method} delivered={result.delivered}")
    if result.detail:
        print(f"URL: {result.detail}")
    return 0 if result.delivered else 1


if __name__ == "__main__":
    raise SystemExit(main())
