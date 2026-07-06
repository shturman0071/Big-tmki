#!/usr/bin/env python3
"""Legal Corpus Curator — dry-run / fetch по whitelist из legal-corpus-catalog.json.

MUST: только URL из каталога (официальные источники).
НЕ использовать fetch-mcp без whitelist.

Примеры:
  python scripts/legal_corpus_curator.py --dry-run
  python scripts/legal_corpus_curator.py --fetch --limit 3
  python scripts/legal_corpus_curator.py --firecrawl   # если FIRECRAWL_API_KEY задан
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "schemas" / "document" / "legal-corpus-catalog.json"
OUT_DIR = ROOT / "runtime" / "artifacts" / "legal-corpus"


def _load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _iter_documents(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for cat in catalog.get("categories", []):
        for doc in cat.get("documents", []):
            docs.append(
                {
                    "category": cat.get("id"),
                    "doc_key": doc.get("doc_key"),
                    "title": doc.get("title"),
                    "monitor_urls": doc.get("monitor_urls") or [],
                }
            )
    return docs


def _fetch_url(url: str, *, timeout: int = 30) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "TMKI-Legal-Corpus-Curator/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        ctype = resp.headers.get("Content-Type", "unknown")
        return body, ctype


def _firecrawl_scrape(url: str) -> str | None:
    api_key = os.environ.get("FIRECRAWL_API_KEY", "")
    if not api_key:
        return None
    payload = json.dumps({"url": url}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.firecrawl.dev/v1/scrape",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return (data.get("data") or {}).get("markdown") or (data.get("data") or {}).get("content")
    except (urllib.error.URLError, json.JSONDecodeError, KeyError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Legal Corpus Curator (whitelist only)")
    parser.add_argument("--dry-run", action="store_true", help="Только список URL из каталога")
    parser.add_argument("--fetch", action="store_true", help="Скачать первые байты с whitelist URL")
    parser.add_argument("--firecrawl", action="store_true", help="Использовать Firecrawl если есть ключ")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    args = parser.parse_args()

    if not args.catalog.is_file():
        print(f"Каталог не найден: {args.catalog}", file=sys.stderr)
        return 1

    catalog = _load_catalog()
    docs = _iter_documents(catalog)
    print(f"Каталог: {len(docs)} документов, schedule={catalog.get('update_schedule')}")

    if args.dry_run or not args.fetch:
        for doc in docs[: args.limit]:
            print(f"  [{doc['doc_key']}] {doc['title']}")
            for url in doc["monitor_urls"]:
                print(f"    - {url}")
        if args.dry_run:
            return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    fetched = 0
    for doc in docs:
        if fetched >= args.limit:
            break
        for url in doc["monitor_urls"]:
            if fetched >= args.limit:
                break
            print(f"fetch {doc['doc_key']}: {url}")
            try:
                if args.firecrawl:
                    text = _firecrawl_scrape(url)
                    if text:
                        content = text.encode("utf-8")
                        ctype = "text/markdown"
                    else:
                        content, ctype = _fetch_url(url)
                else:
                    content, ctype = _fetch_url(url)
                digest = hashlib.sha256(content).hexdigest()
                manifest.append(
                    {
                        "doc_key": doc["doc_key"],
                        "url": url,
                        "sha256": digest,
                        "content_type": ctype,
                        "bytes": len(content),
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                fetched += 1
            except urllib.error.URLError as exc:
                print(f"  ошибка: {exc.reason}")
                manifest.append({"doc_key": doc["doc_key"], "url": url, "error": str(exc.reason)})

    out = OUT_DIR / "fetch-manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Manifest: {out} ({len(manifest)} записей)")
    print("Следующий шаг: ingest с classification=public/internal + audit regulatory_corpus_updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
