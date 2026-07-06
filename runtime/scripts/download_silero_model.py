#!/usr/bin/env python3
"""Скачать Silero TTS v5_3_ru (~140 МБ) в runtime/models/silero/."""

from __future__ import annotations

import argparse
import ssl
import sys
import urllib.request
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
DEFAULT_URL = "https://models.silero.ai/models/tts/ru/v5_3_ru.pt"
DEFAULT_OUT = Path.home() / ".local" / "share" / "tmki-models" / "silero" / "v5_3_ru.pt"


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".pt.part")
    print(f"Downloading {url}", flush=True)
    print(f"  -> {dest}", flush=True)
    ctx = ssl.create_default_context()
    try:
        urllib.request.urlretrieve(url, tmp)  # noqa: S310
    except Exception:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(url, context=ctx) as resp:  # noqa: S310
            tmp.write_bytes(resp.read())
    tmp.replace(dest)
    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"OK: {size_mb:.1f} MB", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Silero v5_3_ru model")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.out.is_file() and not args.force and args.out.stat().st_size > 5_000_000:
        print(f"Already exists: {args.out} ({args.out.stat().st_size // (1024*1024)} MB)")
        return 0
    try:
        _download(args.url, args.out)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
