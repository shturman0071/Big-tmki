# Дождаться 100% re-index и запустить finalize (без milestone/pgvector sync до 100%)
param(
    [int]$PollSeconds = 120,
    [string]$Query = "промбезопасность кран"
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"
$env:TMKI_MVP_MESSAGE = $Query
Set-Location $runtime

Write-Host "=== Wait for re-index 100% ===" -ForegroundColor Cyan
if ($PollSeconds -gt 0) {
    python scripts/wait_reindex_complete.py --poll-seconds $PollSeconds
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    python scripts/wait_reindex_complete.py --once
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "=== Preflight ===" -ForegroundColor Cyan
python scripts/preflight_finalize.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Preflight failed — исправьте и запустите finalize вручную." -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Write-Host "=== Export audit ===" -ForegroundColor Cyan
python scripts/export_reindex_audit.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Ops bundle + handoff ===" -ForegroundColor Cyan
python scripts/export_reindex_ops_bundle.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/print_reindex_handoff.py --save (Join-Path $runtime "artifacts\regulations-import\reindex-handoff.txt")

& $PSScriptRoot\finalize_regulations_index.ps1 -Query $Query
