import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_load_legal_corpus_catalog():
    from tmki_legal import load_legal_corpus_catalog, iter_catalog_documents

    catalog = load_legal_corpus_catalog(ROOT / "schemas/document/legal-corpus-catalog.json")
    docs = list(iter_catalog_documents(catalog))
    assert len(docs) >= 16
    assert any(d["doc_key"] == "fz_116_opo" for d in docs)


def test_run_legal_corpus_curator_dry_run(monkeypatch, tmp_path):
    def fake_probe(doc, timeout=10.0):
        return {
            "doc_key": doc["doc_key"],
            "title": doc.get("title"),
            "primary": {
                "url": doc.get("monitor_urls", [""])[0],
                "ok": True,
                "status": 200,
                "content_hash": f"sha256:fixed-{doc['doc_key']}",
            },
            "probes": [],
        }

    monkeypatch.setattr("tmki_legal.curator.probe_document_sources", fake_probe)
    from tmki_legal import run_legal_corpus_curator

    r1 = run_legal_corpus_curator(state_dir=tmp_path, dry_run=False)
    assert r1["checked"] >= 16
    assert r1["changed"] == r1["checked"]

    r2 = run_legal_corpus_curator(state_dir=tmp_path, dry_run=False)
    assert r2["changed"] == 0


def test_apply_pending_legal_updates(tmp_path):
    updates_file = tmp_path / "regulatory-updates.json"
    updates_file.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "updates": [
                    {
                        "schema_version": "0.1",
                        "doc_key": "fz_116_opo",
                        "update_type": "amendment",
                        "source_url": "https://example.test/fz116",
                        "detected_at": "2026-07-01T12:00:00Z",
                        "ingest_status": "pending",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def fake_fetch(url: str, **kwargs: object) -> bytes:
        return b"<html><body>116-FZ prombez text sample</body></html>"

    from tmki_legal import apply_pending_legal_updates

    result = apply_pending_legal_updates(state_dir=tmp_path, fetcher=fake_fetch)
    assert result["pending"] == 1
    assert result["applied"] == 1
    assert result["results"][0]["chunks"] >= 1

    saved = json.loads(updates_file.read_text(encoding="utf-8"))
    assert saved["updates"][0]["ingest_status"] == "ingested"


def test_apply_pending_legal_updates_dry_run(tmp_path):
    updates_file = tmp_path / "regulatory-updates.json"
    updates_file.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "updates": [
                    {
                        "doc_key": "fz_116_opo",
                        "ingest_status": "pending",
                        "source_url": "https://example.test/fz116",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    from tmki_legal import apply_pending_legal_updates

    result = apply_pending_legal_updates(state_dir=tmp_path, dry_run=True)
    assert result["pending"] == 1
    assert result["applied"] == 0
    saved = json.loads(updates_file.read_text(encoding="utf-8"))
    assert saved["updates"][0]["ingest_status"] == "pending"
