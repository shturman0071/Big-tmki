#!/usr/bin/env python3
"""Проверка Docker daemon перед finalize."""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Docker daemon for pgvector finalize")
    parser.add_argument("--require", action="store_true", help="Exit 1 if Docker not ready")
    args = parser.parse_args()

    from tmki_runtime.docker_check import docker_daemon_ready

    ok, detail = docker_daemon_ready()
    if ok:
        print(f"docker: ok ({detail})")
        return 0
    print(f"docker: not ready ({detail})", file=sys.stderr)
    return 1 if args.require else 0


if __name__ == "__main__":
    raise SystemExit(main())
