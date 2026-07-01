#!/usr/bin/env python3
"""Smoke-test HTTP OCR (MinerU / Mistral) с реальным или mock endpoint."""

from __future__ import annotations

import argparse
import json
import os
import sys


def _sample_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\nTMKI HTTP OCR smoke test."


def main() -> int:
    parser = argparse.ArgumentParser(description="HTTP OCR smoke test")
    parser.add_argument("--file", type=argparse.FileType("rb"), help="Файл для OCR (иначе встроенный sample)")
    parser.add_argument("--mock", action="store_true", help="Mock HTTP без реальных URL")
    args = parser.parse_args()

    raw = args.file.read() if args.file else _sample_bytes()
    os.environ["TMKI_OCR_MODE"] = "http"

    if args.mock:
        from tmki_ocr.ocr import HttpMinerUProvider, HttpMistralOcrProvider, run_ocr

        def fake_post(url: str, payload: dict, headers: dict, timeout: int) -> dict:
            return {
                "markdown": "HTTP OCR mock: промбезопасность кран маркшейдерская съёмка.",
                "page_count": 1,
                "avg_confidence": 0.9,
            }

        result = run_ocr(
            doc_id="http_smoke",
            trace_id="http-smoke",
            raw_bytes=raw,
            mineru_provider=HttpMinerUProvider(api_url="http://mock/mineru", http_post=fake_post),
            mistral_provider=HttpMistralOcrProvider(api_url="http://mock/mistral", http_post=fake_post),
        )
        print(json.dumps({k: v for k, v in result.items() if not k.startswith("_")}, ensure_ascii=False, indent=2))
        return 0 if result["ocr_status"] == "completed" else 1

    mineru = os.environ.get("MINERU_API_URL", "")
    mistral = os.environ.get("MISTRAL_OCR_API_URL", "")
    if not mineru and not mistral:
        print("Задайте MINERU_API_URL и/или MISTRAL_OCR_API_URL, или --mock", file=sys.stderr)
        return 1

    import subprocess
    from pathlib import Path

    probe = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "check_ocr_http.py")],
        capture_output=True,
        text=True,
    )
    print(probe.stdout.rstrip() or probe.stderr.rstrip())
    if probe.returncode != 0:
        return 1

    from tmki_ocr.ocr import run_ocr

    result = run_ocr(doc_id="http_smoke", trace_id="http-smoke", raw_bytes=raw)
    print(json.dumps({k: v for k, v in result.items() if not k.startswith("_")}, ensure_ascii=False, indent=2))
    return 0 if result["ocr_status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
