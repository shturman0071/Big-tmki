# Быстрый demo: health → report → MVP (stub)
param(
    [string]$Query = "промбезопасность кран",
    [ValidateSet("json", "pgvector")]
    [string]$Backend = "json",
    [switch]$Experience
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"
$env:TMKI_MVP_MESSAGE = $Query
Set-Location $runtime

Write-Host "=== TMKI demo ===" -ForegroundColor Cyan
python scripts/check_runtime_health.py
python scripts/reindex_report.py

$mvpArgs = @("scripts/run_mvp_regulations.py", "--variant", "v2", "--hybrid")
if ($Backend -eq "pgvector") {
    $env:DATABASE_URL = "postgresql://tmki:tmki_dev@127.0.0.1:5432/tmki"
    $env:TMKI_INDEX_BACKEND = "pgvector"
    $mvpArgs += @("--backend", "pgvector")
}
if ($Experience) {
    $mvpArgs += @("--tts", "--cast", "tv")
}
python @mvpArgs
