#!/usr/bin/env python3
"""Скачать preset Piper-голос (бесплатно с HuggingFace)."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

DEFAULT_VOICE = "ru_RU-ruslan-medium"


def hf_base_for_voice(voice_id: str) -> str:
    m = re.match(r"^([a-z]{2})_([A-Z]{2})-([^-]+)-([^-]+)$", voice_id)
    if not m:
        raise ValueError(f"unsupported voice id: {voice_id}")
    lang, region, name, quality = m.groups()
    return (
        f"https://huggingface.co/rhasspy/piper-voices/resolve/main/"
        f"{lang}/{lang}_{region}/{name}/{quality}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Piper voice model")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path.home() / ".local" / "share" / "piper-voices",
    )
    args = parser.parse_args()

    hf_base = hf_base_for_voice(args.voice)
    args.dir.mkdir(parents=True, exist_ok=True)
    files = [
        (f"{args.voice}.onnx", f"{hf_base}/{args.voice}.onnx"),
        (f"{args.voice}.onnx.json", f"{hf_base}/{args.voice}.onnx.json"),
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
