# Финализация после 100% re-index: pgvector + IVFFlat + quality + MVP
param(
    [string]$Query = "промбезопасность кран"
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"
$env:TMKI_MVP_MESSAGE = $Query
Set-Location $runtime

python scripts/reindex_report.py --json | Out-Null
$report = python scripts/reindex_report.py --json | ConvertFrom-Json
if ($report.live_progress -lt $report.total) {
    Write-Host "Re-index не завершён: $($report.live_progress)/$($report.total). Дождитесь 100%." -ForegroundColor Yellow
    exit 1
}

Write-Host "=== Finalize regulations index ===" -ForegroundColor Cyan
& $PSScriptRoot\setup_pgvector_v2.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "IVFFlat index..."
python scripts/load_regulations_pgvector.py --variant v2
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python scripts/compare_chunks_quality.py
python scripts/run_mvp_regulations.py --variant v2 --backend pgvector --hybrid
Write-Host "Done."
