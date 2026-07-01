# TMKI local stack
Set-Location $PSScriptRoot\..\docker
docker compose -f docker-compose.full.yml up -d postgres
Write-Host ""
Write-Host "Postgres: postgresql://tmki:tmki_dev@127.0.0.1:5432/tmki"
Write-Host "Optional LLM: docker compose -f docker-compose.full.yml --profile llm up -d ollama"
Write-Host "Env template: docker/env.production.example"
Write-Host "Health: python scripts/check_runtime_health.py"
