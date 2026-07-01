#!/usr/bin/env python3
"""Ожидание готовности Docker daemon."""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait for Docker daemon")
    parser.add_argument("--timeout", type=int, default=600, help="Seconds to wait")
    parser.add_argument("--poll", type=int, default=10, help="Poll interval seconds")
    parser.add_argument("--once", action="store_true", help="Single check only")
    args = parser.parse_args()

    from tmki_runtime.docker_check import docker_daemon_ready, wait_for_docker

    if args.once:
        ok, detail = docker_daemon_ready()
    else:
        print(f"waiting for docker (timeout={args.timeout}s, poll={args.poll}s)...", file=sys.stderr)
        ok, detail = wait_for_docker(timeout_sec=args.timeout, poll_sec=args.poll)

    if ok:
        print(f"docker: ok ({detail})")
        return 0
    print(f"docker: not ready ({detail})", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
