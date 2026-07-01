# Поднять Postgres+pgvector и загрузить текущий chunks-v2 (можно частичный)
Set-Location $PSScriptRoot\..\docker
docker compose -f docker-compose.full.yml up -d postgres
Start-Sleep -Seconds 8

$env:DATABASE_URL = "postgresql://tmki:tmki_dev@127.0.0.1:5432/tmki"
$env:TMKI_INDEX_BACKEND = "pgvector"
$env:TMKI_EMBEDDING_PROVIDER = "local"
$env:TMKI_EMBEDDING_DIMS = "64"
$env:PYTHONPATH = (Resolve-Path $PSScriptRoot\..).Path

Set-Location $PSScriptRoot\..
Write-Host "Smoke test..."
python scripts/pgvector_smoke.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Load regulations v2..."
python scripts/load_regulations_pgvector.py --variant v2 --skip-ivfflat
Write-Host "Done. IVFFlat после полного re-index: python scripts/load_regulations_pgvector.py --variant v2"
