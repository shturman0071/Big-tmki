# Еженедельный curator + ingest pending обновлений (без сети — только если есть regulatory-updates.json)
$env:PYTHONPATH = (Resolve-Path $PSScriptRoot\..).Path
Set-Location (Resolve-Path $PSScriptRoot\..).Path
python scripts/run_legal_corpus_curator.py --apply-ingest
