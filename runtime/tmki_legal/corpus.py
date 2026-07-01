from __future__ import annotations

import json
import hashlib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "schemas" / "document" / "legal-corpus-catalog.json"


def load_legal_corpus_catalog(path: Path | None = None) -> dict[str, Any]:
    target = path or DEFAULT_CATALOG
    if not target.is_file():
        raise FileNotFoundError(f"legal corpus catalog не найден: {target}")
    return json.loads(target.read_text(encoding="utf-8"))


def iter_catalog_documents(catalog: dict[str, Any]) -> Iterator[dict[str, Any]]:
    for category in catalog.get("categories", []):
        cat_id = category.get("id", "")
        for doc in category.get("documents", []):
            yield {**doc, "category_id": cat_id}


def _fetch_fingerprint(url: str, timeout: float = 10.0) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "tmki-legal-curator/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(65536)
            return {
                "url": url,
                "ok": True,
                "status": resp.status,
                "etag": resp.headers.get("ETag"),
                "last_modified": resp.headers.get("Last-Modified"),
                "content_hash": "sha256:" + hashlib.sha256(body).hexdigest(),
                "bytes_sampled": len(body),
            }
    except urllib.error.HTTPError as exc:
        return {"url": url, "ok": exc.code in {401, 403, 405}, "status": exc.code}
    except Exception as exc:
        return {"url": url, "ok": False, "error": str(exc)}


def probe_document_sources(doc: dict[str, Any], *, timeout: float = 10.0) -> dict[str, Any]:
    """Проверка доступности источников документа (первая успешная или первая в списке)."""
    download_url = doc.get("download_url")
    urls = [download_url] if download_url else list(doc.get("monitor_urls", []))
    probes: list[dict[str, Any]] = []
    primary: dict[str, Any] | None = None
    for url in urls:
        if not url:
            continue
        probe = _fetch_fingerprint(url, timeout=timeout)
        probes.append(probe)
        if probe.get("ok") and primary is None:
            primary = probe
    return {
        "doc_key": doc["doc_key"],
        "title": doc.get("title", ""),
        "probes": probes,
        "primary": primary,
    }
