"""Debug doc search for Положение о нарядной системе."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME))

QUERY = "найди документ Положение о нарядной системе"

req = urllib.request.Request(
    "http://127.0.0.1:8770/api/agent/doc-search",
    data=json.dumps({"question": QUERY, "corpus": "skru-2", "limit": 20}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    data = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    print("query", data.get("query"))
    print("total", data.get("total"))
    for item in (data.get("items") or [])[:10]:
        print("-", item.get("score"), item.get("relative_path"))
except Exception as e:
    print("error", e)

from tmki_demo.qa import extract_doc_search_query, search_agent_documents

q = extract_doc_search_query(QUERY)
print("extracted", repr(q))
local = search_agent_documents(QUERY, corpus_id="skru-2", limit=20)
print("local total", local.get("total"))
for item in (local.get("items") or [])[:10]:
    print("L-", item.get("score"), item.get("source"), item.get("relative_path"))

from tmki_demo.qa import _get_catalog

cat = _get_catalog(corpus_id="skru-2")
print("archive", cat.archive_root)
print("paths count", len(cat.paths))
matches = cat.search_paths("Положение о нарядной системе", limit=10)
print("direct search_paths", len(matches))
for m in matches[:5]:
    print("M-", m.get("score"), m.get("relative_path"))
