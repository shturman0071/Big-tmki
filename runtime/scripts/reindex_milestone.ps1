# Milestone: incremental pgvector + quality benchmark (25/50/75/100%)
$runtime = Resolve-Path $PSScriptRoot\..
$markerDir = Join-Path $runtime "artifacts\regulations-import\milestones"
$env:PYTHONPATH = $runtime.Path
Set-Location $runtime

if (-not (Test-Path $markerDir)) { New-Item -ItemType Directory -Path $markerDir | Out-Null }

$report = python scripts/reindex_report.py --json | ConvertFrom-Json
$pct = [math]::Floor($report.percent / 25) * 25
if ($pct -lt 25) {
    Write-Host "Progress $($report.percent)% — milestone not reached (need 25%)"
    exit 0
}
if ($report.live_progress -ge $report.total) { $pct = 100 }

$marker = Join-Path $markerDir "milestone-$pct.json"
if (Test-Path $marker) {
    Write-Host "Milestone ${pct}% already done"
    exit 0
}

Write-Host "=== Milestone ${pct}% ===" -ForegroundColor Cyan
python scripts/reindex_report.py
& $PSScriptRoot\sync_pgvector_incremental.ps1
python scripts/compare_chunks_quality.py --save (Join-Path $runtime "artifacts\regulations-import\quality-benchmark-p$pct.json")
@{ percent = $pct; at = (Get-Date).ToUniversalTime().ToString("o") } | ConvertTo-Json | Set-Content $marker -Encoding utf8
Write-Host "Milestone ${pct}% saved."
