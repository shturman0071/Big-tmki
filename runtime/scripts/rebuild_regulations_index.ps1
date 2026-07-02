# Пересборка индекса регламентов: chunks-v2 + полная перезапись pgvector
param(
    [string]$Archive = "D:\Курсор\СКРУ-2",
    [switch]$Fresh,
    [switch]$Resume,
    [switch]$PgvectorOnly,
    [switch]$SkipIvfflat
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"
Set-Location $runtime

function Start-Postgres {
    Set-Location (Join-Path $runtime "docker")
    docker compose -f docker-compose.full.yml up -d postgres
    Start-Sleep -Seconds 8
    Set-Location $runtime
    $env:DATABASE_URL = "postgresql://tmki:tmki_dev@127.0.0.1:5432/tmki"
    $env:TMKI_INDEX_BACKEND = "pgvector"
    if (-not $env:TMKI_EMBEDDING_PROVIDER) { $env:TMKI_EMBEDDING_PROVIDER = "local" }
    if (-not $env:TMKI_EMBEDDING_DIMS) { $env:TMKI_EMBEDDING_DIMS = "64" }
}

function Sync-PgvectorReplace {
    param([switch]$NoIvfflat)
    Start-Postgres
    python -c "import psycopg" 2>$null
    if ($LASTEXITCODE -ne 0) {
        pip install "psycopg[binary]>=3.2"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    $loadArgs = @("scripts/load_regulations_pgvector.py", "--variant", "v2", "--replace")
    if ($NoIvfflat) { $loadArgs += "--skip-ivfflat" }
    python @loadArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($PgvectorOnly) {
    Write-Host "=== Rebuild index: pgvector only (from chunks-v2) ===" -ForegroundColor Cyan
    Sync-PgvectorReplace -NoIvfflat:(-not $SkipIvfflat)
    Write-Host "Done. chunks-v2 не менялся; pgvector перезаписан." -ForegroundColor Green
    exit 0
}

if ($Fresh -and $Resume) {
    Write-Host "Use either -Fresh or -Resume, not both." -ForegroundColor Yellow
    exit 1
}

Write-Host "=== Rebuild regulations index ===" -ForegroundColor Cyan
Write-Host "  Archive: $Archive" -ForegroundColor DarkGray

$reindexArgs = @("scripts/reindex_regulations_local.py", "--archive", $Archive, "--checkpoint-every", "200")
if ($Fresh) {
    $reindexArgs += "--no-resume"
    Write-Host "  Mode: fresh re-index (chunks-v2 from scratch)" -ForegroundColor DarkGray
} else {
    Write-Host "  Mode: resume re-index" -ForegroundColor DarkGray
}

$env:TMKI_OCR_MODE = "local"
python @reindexArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Sync pgvector (full replace) ===" -ForegroundColor Cyan
Sync-PgvectorReplace -NoIvfflat:$SkipIvfflat

Write-Host "Done." -ForegroundColor Green
Write-Host "  chunks: artifacts/regulations-import/chunks-v2.json" -ForegroundColor DarkGray
Write-Host "  pgvector: DATABASE_URL + tmki_chunks (replace)" -ForegroundColor DarkGray
Write-Host "  После 100% re-index: .\scripts\run_finalize.ps1" -ForegroundColor DarkGray
