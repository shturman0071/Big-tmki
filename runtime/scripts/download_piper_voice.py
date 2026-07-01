#!/usr/bin/env python3
"""Скачать preset Piper-голос (бесплатно с HuggingFace)."""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

DEFAULT_VOICE = "ru_RU-denis-medium"
HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/denis/medium"


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Piper voice model")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path.home() / ".local" / "share" / "piper-voices",
    )
    args = parser.parse_args()

    args.dir.mkdir(parents=True, exist_ok=True)
    files = [
        (f"{args.voice}.onnx", f"{HF_BASE}/{args.voice}.onnx"),
        (f"{args.voice}.onnx.json", f"{HF_BASE}/{args.voice}.onnx.json"),
    ]
    for name, url in files:
        dest = args.dir / name
        if dest.is_file():
            print(f"skip {dest}")
            continue
        print(f"download {url} -> {dest}")
        urllib.request.urlretrieve(url, dest)
    print(f"Готово. PIPER_VOICE={args.voice} PIPER_VOICE_DIR={args.dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
