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
python scripts/export_reindex_audit.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $PSScriptRoot\setup_pgvector_v2.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:DATABASE_URL = "postgresql://tmki:tmki_dev@127.0.0.1:5432/tmki"
$env:TMKI_INDEX_BACKEND = "pgvector"

Write-Host "IVFFlat index..."
python scripts/load_regulations_pgvector.py --variant v2
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$qualityPath = Join-Path $runtime "artifacts\regulations-import\quality-benchmark-final.json"
python scripts/compare_chunks_quality.py --hybrid --save $qualityPath
python scripts/benchmark_regulations_search.py --variant v2 --hybrid --backend pgvector
python scripts/run_mvp_regulations.py --variant v2 --backend pgvector --hybrid
python scripts/post_finalize_report.py
python scripts/print_reindex_handoff.py --finalize --save (Join-Path $runtime "artifacts\regulations-import\finalize-handoff.txt")
@{ done_at = (Get-Date).ToUniversalTime().ToString("o") } | ConvertTo-Json | Set-Content (Join-Path $runtime "artifacts\regulations-import\finalize-done.json") -Encoding utf8
Write-Host "Done."
