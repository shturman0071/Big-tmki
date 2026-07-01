# Incremental sync chunks-v2 → pgvector (во время re-index)
Set-Location (Resolve-Path $PSScriptRoot\..\docker).Path
docker compose -f docker-compose.full.yml up -d postgres
Start-Sleep -Seconds 8

$env:DATABASE_URL = "postgresql://tmki:tmki_dev@127.0.0.1:5432/tmki"
$env:TMKI_INDEX_BACKEND = "pgvector"
$env:TMKI_EMBEDDING_PROVIDER = "local"
$env:TMKI_EMBEDDING_DIMS = "64"
$env:PYTHONPATH = (Resolve-Path $PSScriptRoot\..).Path

Set-Location (Resolve-Path $PSScriptRoot\..).Path
python scripts/load_regulations_pgvector.py --variant v2 --incremental --skip-ivfflat
