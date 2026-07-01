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
